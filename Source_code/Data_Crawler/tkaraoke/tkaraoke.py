#!/usr/bin/env python3
"""
tkaraoke_harvest.py
Combine search-prefix crawling + ID sweep + metadata fetching.
Stores results in SQLite (tkaraoke.db) and can export CSV.

Usage:
    python tkaraoke_harvest.py
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
import time
import random
import sqlite3
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import deque
from tqdm import tqdm
import csv
import os
import sys
import signal

# ----------------- CONFIG -----------------
BASE = "https://lyric.tkaraoke.com"
SEARCH_PATH = "/SearchResult.aspx"
SONG_URL_PATTERN = re.compile(r"/\d+/.+\.html$")
# If site uses p for pages, this handles that. Adjust if pagination param different.
PAGE_PARAM_NAME = "p"

DB_FILE = "tkaraoke.db"
OUTPUT_CSV = "tkaraoke_full_metadata.csv"

# crawling params
START_KEYS = list("abcdefghijklmnopqrstuvwxyz0123456789")
EXPAND_THRESHOLD = 30      # if >= results -> expand prefix
MAX_KEY_ITER = 100000      # stop prefix expansion after this many keywords processed
MAX_PREFIX_LEN = 5         # max depth of prefix expansion
SLEEP_BETWEEN_REQ = 0.5    # base delay between requests per worker (randomized)
CONCURRENCY = 5            # number of worker threads for metadata fetching / ID sweep
MAX_ID = 120000            # upper bound for ID sweep (adjust to expected range)
ID_BATCH_SIZE = 1000       # stash IDs in DB in batches

# network
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; Tkrawler/1.0; +your-email@example.com)"
}
REQUEST_TIMEOUT = 15
MAX_RETRIES = 3
# ------------------------------------------

# SQLite helper
LOCK = threading.Lock()

def init_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    # table for urls to process or discovered
    c.execute("""
    CREATE TABLE IF NOT EXISTS urls (
        url TEXT PRIMARY KEY,
        discovered_by TEXT,
        processed INTEGER DEFAULT 0,
        last_error TEXT,
        title TEXT,
        artist TEXT,
        lyrics TEXT,
        has_audio INTEGER DEFAULT 0,
        has_karaoke INTEGER DEFAULT 0,
        has_sheet INTEGER DEFAULT 0,
        id_num INTEGER
    )
    """)
    # simple meta table
    c.execute("""
    CREATE TABLE IF NOT EXISTS meta (
        k TEXT PRIMARY KEY,
        v TEXT
    )
    """)
    conn.commit()
    return conn

# network utilities
session = requests.Session()
session.headers.update(HEADERS)

def get_url(url, params=None, retry=MAX_RETRIES):
    backoff = 1.0
    for attempt in range(retry):
        try:
            resp = session.get(url, params=params, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                return resp.text
            else:
                # return body for 404 etc (we handle)
                return resp.text
        except Exception as e:
            time.sleep(backoff + random.random()*0.5)
            backoff *= 2
    return None

# parsing utilities
def parse_song_links(html):
    """Return set of absolute song links found in a search result or listing page."""
    if not html:
        return set()
    soup = BeautifulSoup(html, "html.parser")
    links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].split('#')[0]
        if SONG_URL_PATTERN.search(href):
            links.add(urljoin(BASE, href))
    return links

def parse_pagination_pages(html):
    """Try to detect number of pages in search results. Return int >=1."""
    if not html:
        return 1
    soup = BeautifulSoup(html, "html.parser")
    # common patterns: div.pagination a, ul.pagination li a, span.pages, etc.
    # look for numeric links
    nums = []
    for a in soup.find_all("a"):
        txt = a.get_text(strip=True)
        if txt.isdigit():
            try:
                nums.append(int(txt))
            except:
                pass
    return max(nums) if nums else 1

def fetch_and_store_links(conn, url, discovered_by="unknown"):
    links = set()
    html = get_url(url)
    links |= parse_song_links(html)
    with LOCK:
        cur = conn.cursor()
        for l in links:
            try:
                cur.execute("INSERT OR IGNORE INTO urls(url, discovered_by) VALUES (?, ?)", (l, discovered_by))
            except Exception:
                pass
        conn.commit()
    return links

# SEARCH PREFIX CRAWLER (with pagination)
def search_prefix_crawl(conn):
    print("[*] Starting search-prefix crawler")
    queue = deque(START_KEYS)
    processed = set()
    iter_count = 0

    pbar = tqdm(total=MAX_KEY_ITER, desc="search keywords")
    try:
        while queue and iter_count < MAX_KEY_ITER:
            kw = queue.popleft()
            if kw in processed:
                continue

            # get first page
            params = {"kw": kw}
            html = get_url(BASE + SEARCH_PATH, params=params)
            time.sleep(SLEEP_BETWEEN_REQ + random.random()*0.4)
            if html is None:
                # network fail -> requeue to try later
                queue.append(kw)
                continue

            # collect links from first page and subsequent pages
            total_pages = parse_pagination_pages(html)
            links = parse_song_links(html)
            # if more pages, iterate through them
            if total_pages > 1:
                for p in range(2, total_pages+1):
                    params = {"kw": kw, PAGE_PARAM_NAME: p}
                    page_html = get_url(BASE + SEARCH_PATH, params=params)
                    time.sleep(SLEEP_BETWEEN_REQ + random.random()*0.4)
                    links |= parse_song_links(page_html)

            # store discovered links
            with LOCK:
                cur = conn.cursor()
                for l in links:
                    cur.execute("INSERT OR IGNORE INTO urls(url, discovered_by) VALUES (?, ?)", (l, f"search:{kw}"))
                conn.commit()

            hits = len(links)
            iter_count += 1
            pbar.update(1)

            # expansion decision
            if hits >= EXPAND_THRESHOLD and len(kw) < MAX_PREFIX_LEN:
                for ch in "abcdefghijklmnopqrstuvwxyz0123456789":
                    newk = kw + ch
                    if newk not in processed:
                        queue.append(newk)

            processed.add(kw)
            # occasional save progress in meta
            if iter_count % 50 == 0:
                with LOCK:
                    conn.execute("REPLACE INTO meta(k, v) VALUES (?, ?)", ("search_iter", str(iter_count)))
                    conn.commit()
    finally:
        pbar.close()
    print("[*] Search-prefix crawler finished (or reached limit)")

# ID SWEEP: generate URLs by id and insert into DB
def id_sweep(conn, start_id=1, end_id=MAX_ID, batch=ID_BATCH_SIZE):
    print(f"[*] Starting ID sweep {start_id}..{end_id}")
    cur = conn.cursor()
    count = 0
    for start in range(start_id, end_id+1, batch):
        batch_end = min(end_id, start + batch - 1)
        to_insert = []
        for i in range(start, batch_end+1):
            # form URL using id; slug can be dummy
            url = f"{BASE}/{i}/x.html"
            to_insert.append((url, f"id:{i}", 0, None, None, None, None, 0, 0, 0, i))
        with LOCK:
            cur.executemany("INSERT OR IGNORE INTO urls(url, discovered_by, processed, last_error, title, artist, lyrics, has_audio, has_karaoke, has_sheet, id_num) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", to_insert)
            conn.commit()
        count += len(to_insert)
        # small pause after batch
        time.sleep(0.2 + random.random()*0.5)
    print(f"[*] ID sweep inserted batches up to {end_id}")

# METADATA FETCHER
def extract_metadata_from_song_page(html, url):
    """Return dict with title, artist, lyrics, has_audio, has_karaoke, has_sheet"""
    r = {"title": None, "artist": None, "lyrics": None, "has_audio": 0, "has_karaoke": 0, "has_sheet": 0}
    if not html:
        return r
    soup = BeautifulSoup(html, "html.parser")
    # title
    t = soup.find("h3", class_="h3-title-song")
    if t:
        r["title"] = t.get_text(strip=True)
    # artist
    a = soup.find("div", class_="div-author")
    if a:
        r["artist"] = a.get_text(strip=True)
    # lyrics
    lyrics_div = soup.find("div", class_="div-content-lyric")
    if lyrics_div:
        r["lyrics"] = "\n".join([s.strip() for s in lyrics_div.stripped_strings])

    # heuristics for audio / karaoke / sheet music:
    # audio: presence of play buttons, "DownloadMp3.aspx", or audio tags
    if soup.find("audio") is not None:
        r["has_audio"] = 1
    if soup.find(href=re.compile(r"DownloadMp3\.aspx")):
        r["has_audio"] = 1
    # karaoke: presence of "KaraokeLyric.aspx" link or words "Karaoke"
    if soup.find(href=re.compile(r"KaraokeLyric\.aspx")) or soup.find(string=re.compile(r"Karaoke", re.I)):
        r["has_karaoke"] = 1
    # sheet music: ViewMusicSheet.aspx or text like "nốt nhạc"
    if soup.find(href=re.compile(r"ViewMusicSheet\.aspx")) or soup.find(string=re.compile(r"nốt nhạc|nốt nhạc", re.I)):
        r["has_sheet"] = 1

    # fallback: sometimes audio icon class or data attributes
    # check for common classes/ids (site specific; tweak if you find patterns)
    if soup.select_one(".btn-play") or soup.select_one(".play-btn"):
        r["has_audio"] = 1

    return r

def worker_fetch_metadata(conn, url_row):
    """
    url_row: tuple from DB: (url, discovered_by, processed, last_error, title, artist, lyrics, has_audio, has_karaoke, has_sheet, id_num)
    returns True if fetched/updated, False on skip/failure
    """
    url = url_row[0]
    for attempt in range(MAX_RETRIES):
        html = get_url(url)
        time.sleep(SLEEP_BETWEEN_REQ + random.random()*0.6)  # polite pause
        if html is None:
            continue
        # check if page looks like valid song (has lyric container)
        meta = extract_metadata_from_song_page(html, url)
        # if no title and no lyrics, treat as non-existing (or 404)
        if not meta["title"] and not meta["lyrics"]:
            # mark processed but empty
            with LOCK:
                conn.execute("UPDATE urls SET processed=1, last_error=? WHERE url=?", ("no_content", url))
                conn.commit()
            return False
        # else update DB
        with LOCK:
            conn.execute("""
                UPDATE urls SET processed=1, last_error=NULL, title=?, artist=?, lyrics=?, has_audio=?, has_karaoke=?, has_sheet=? WHERE url=?
            """, (meta["title"], meta["artist"], meta["lyrics"], meta["has_audio"], meta["has_karaoke"], meta["has_sheet"], url))
            conn.commit()
        return True
    # exhausted retries
    with LOCK:
        conn.execute("UPDATE urls SET last_error=? WHERE url=?", ("failed_retries", url))
        conn.commit()
    return False

def fetch_all_metadata(conn, limit=None, concurrency=CONCURRENCY):
    """Fetch metadata for unprocessed urls. limit = max items to fetch this run."""
    cur = conn.cursor()
    # select unprocessed rows
    q = "SELECT url, discovered_by, processed, last_error, title, artist, lyrics, has_audio, has_karaoke, has_sheet, id_num FROM urls WHERE processed=0"
    if limit:
        q += " LIMIT %d" % limit
    rows = cur.execute(q).fetchall()
    print(f"[*] Metadata fetcher - {len(rows)} items to process (concurrency={concurrency})")
    if not rows:
        return
    with ThreadPoolExecutor(max_workers=concurrency) as exe:
        futures = {exe.submit(worker_fetch_metadata, conn, r): r[0] for r in rows}
        for fut in tqdm(as_completed(futures), total=len(futures), desc="fetching metadata"):
            try:
                fut.result()
            except Exception as e:
                # store error
                url = futures[fut]
                with LOCK:
                    conn.execute("UPDATE urls SET last_error=? WHERE url=?", (str(e), url))
                    conn.commit()

def export_to_csv(conn, output=OUTPUT_CSV):
    cur = conn.cursor()
    rows = cur.execute("SELECT url, discovered_by, title, artist, has_audio, has_karaoke, has_sheet FROM urls WHERE title IS NOT NULL OR has_audio=1").fetchall()
    with open(output, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["url", "discovered_by", "title", "artist", "has_audio", "has_karaoke", "has_sheet"])
        for r in rows:
            writer.writerow(r)
    print(f"[*] Exported {len(rows)} rows to {output}")

# Graceful stop
STOP_EVENT = threading.Event()
def signal_handler(sig, frame):
    print("\n[!] Received stop signal. Will finish current work and exit gracefully...")
    STOP_EVENT.set()

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Main orchestration
def main():
    print("WARNING: This script will aggressively crawl lyric.tkaraoke.com if configured. Use responsibly.")
    conn = init_db()

    # Step A: run search-prefix crawler (fills DB with discovered URLs)
    search_prefix_crawl(conn)

    if STOP_EVENT.is_set():
        print("[*] Stopped after search phase")
        export_to_csv(conn)
        return

    # Step B: ID sweep fallback - insert candidate URLs formed by id
    id_sweep(conn, start_id=1, end_id=MAX_ID)

    if STOP_EVENT.is_set():
        print("[*] Stopped after id sweep")
        export_to_csv(conn)
        return

    # Step C: Fetch metadata in batches until all processed
    # loop: fetch metadata for a chunk, then re-evaluate until no unprocessed left
    while not STOP_EVENT.is_set():
        # fetch up to a batch (limit optional)
        fetch_all_metadata(conn, limit=CONCURRENCY * 50, concurrency=CONCURRENCY)
        # check if any unprocessed remains
        cur = conn.cursor()
        remaining = cur.execute("SELECT COUNT(*) FROM urls WHERE processed=0").fetchone()[0]
        print(f"[*] Remaining unprocessed: {remaining}")
        if remaining == 0:
            break
        # if still many remain, sleep a bit and continue
        time.sleep(1.0)
    # Final export
    export_to_csv(conn)
    conn.close()
    print("[*] Done.")

if __name__ == "__main__":
    main()
