import requests
from bs4 import BeautifulSoup
import time
from urllib.parse import urljoin
import os

# --- Cấu hình ---
SITEMAP_INDEX_URL = "https://nhac.vn/sitemap.xml"
OUTPUT_FILE = "all_song_links.txt"
CHECKPOINT_FILE = "checkpoint.txt"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/91.0.4472.124 Safari/537.36"
}
RATE_LIMIT_DELAY = 1  # giây

# ---------------- Checkpoint helpers ----------------

def init_checkpoint():
    if not os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
            f.write("[Đã duyệt]\n\n[Đang duyệt]\n")

def load_checkpoint():
    completed = []
    current = {"parent_1": None, "child_1": None, "child_2": None}

    section = None
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if line == "[Đã duyệt]":
                    section = "done"
                    continue
                elif line == "[Đang duyệt]":
                    section = "current"
                    continue

                if section == "done" and line.startswith("parent_1:"):
                    completed.append(line.split(":", 1)[1].strip())
                elif section == "current" and ":" in line:
                    k, v = line.split(":", 1)
                    current[k.strip()] = v.strip() or None
    return completed, current


def save_current_checkpoint(parent=None, child1=None, child2=None):
    completed, current = load_checkpoint()
    if parent is not None:
        current["parent_1"] = parent if parent != "" else None
    if child1 is not None:
        current["child_1"] = child1 if child1 != "" else None
    if child2 is not None:
        current["child_2"] = child2 if child2 != "" else None

    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
        f.write("[Đã duyệt]\n")
        for p in completed:
            f.write(f"parent_1: {p}\n")
        f.write("\n[Đang duyệt]\n")
        f.write(f"parent_1: {current['parent_1'] or ''}\n")
        f.write(f"child_1: {current['child_1'] or ''}\n")
        f.write(f"child_2: {current['child_2'] or ''}\n")


def add_completed_parent(parent_url):
    completed, current = load_checkpoint()
    if parent_url not in completed:
        completed.append(parent_url)
    # clear current
    current = {"parent_1": None, "child_1": None, "child_2": None}

    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
        f.write("[Đã duyệt]\n")
        for p in completed:
            f.write(f"parent_1: {p}\n")
        f.write("\n[Đang duyệt]\n")
        f.write("parent_1: \nchild_1: \nchild_2: \n")

    print(f"✅ Hoàn tất {parent_url}, ghi vào [Đã duyệt]")

# ---------------- Fetch helpers ----------------

def fetch_content(url):
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        if response.status_code == 200:
            try:
                return BeautifulSoup(response.text, "lxml")
            except Exception:
                return BeautifulSoup(response.text, "html.parser")
    except requests.exceptions.RequestException as e:
        print(f"Lỗi khi truy cập {url}: {e}")
    return None

# ---------------- Crawl helpers ----------------

def get_song_urls_from_artist_page(artist_songs_url, resume_url=None, seen_urls=None):
    song_urls = []
    if resume_url and "?p=" in resume_url:
        try:
            page = int(resume_url.split("?p=")[-1])
        except Exception:
            page = 1
    else:
        page = 1

    while True:
        current_page_url = artist_songs_url if page == 1 else f"{artist_songs_url}?p={page}"
        print(f"   -> Đang quét trang bài hát: {current_page_url}")
        save_current_checkpoint(child2=current_page_url)

        soup = fetch_content(current_page_url)
        if not soup:
            print("   -> Không tải được trang, dừng.")
            break

        song_links = soup.select("ul.list_song li div.info h3.name a")
        if not song_links:
            print(f"   -> Trang {page} không có bài hát, dừng lại.")
            break

        found_new = False
        for link in song_links:
            href = link.get("href")
            if href and "/bai-hat/" in href:
                full_url = urljoin(current_page_url, href)
                if seen_urls is None or full_url not in seen_urls:
                    song_urls.append(full_url)
                    if seen_urls is not None:
                        seen_urls.add(full_url)
                    found_new = True

        if not found_new:
            print(f"   -> Không tìm thấy bài hát mới ở trang {page}, dừng lại.")
            break

        page += 1
        time.sleep(RATE_LIMIT_DELAY)

    return song_urls


def dfs_crawler(start_url, visited, file_handle, completed_parents, checkpoint, seen_urls):
    if start_url in visited:
        return
    visited.add(start_url)

    if start_url in completed_parents:
        print(f"⏩ Bỏ qua {start_url} (đã duyệt trước đó).")
        return

    print(f"Đang duyệt: {start_url}")
    soup = fetch_content(start_url)
    if not soup:
        return

    loc_tags = soup.find_all("loc")
    is_leaf_sitemap = True

    # --- Sitemap cha ---
    for loc in loc_tags:
        url = loc.get_text(strip=True)
        if "sitemap" in url and url.endswith(".xml"):
            is_leaf_sitemap = False
            if checkpoint.get("parent_1") and url != checkpoint["parent_1"]:
                print(f"  -> Bỏ qua sitemap cha {url} (chưa đến parent_1).")
                continue

            save_current_checkpoint(parent=url)
            time.sleep(RATE_LIMIT_DELAY)
            dfs_crawler(url, visited, file_handle, completed_parents, checkpoint, seen_urls)
            add_completed_parent(url)

    # --- Sitemap lá (nghệ sĩ) ---
    if is_leaf_sitemap:
        print(f"Đã đến sitemap lá: {start_url}. Bắt đầu lấy link nghệ sĩ...")
        for loc in loc_tags:
            url = loc.get_text(strip=True)


            if "/nghe-si/" in url:
                artist_songs_url = url.rstrip("/") + "/bai-hat"

                if checkpoint.get("child_1") and artist_songs_url != checkpoint["child_1"]:
                    print(f"  -> Bỏ qua nghệ sĩ {artist_songs_url} (chưa đến child_1).")
                    continue

                print(f"  -> Quét nghệ sĩ: {artist_songs_url}")
                save_current_checkpoint(child1=artist_songs_url, child2="")
                resume_page = checkpoint.get("child_2")

                new_songs = get_song_urls_from_artist_page(
                    artist_songs_url,
                    resume_url=resume_page,
                    seen_urls=seen_urls
                )

                # ✅ Reset cả file lẫn RAM để tiếp tục đúng
                save_current_checkpoint(child1="", child2="")
                checkpoint["child_1"] = None
                checkpoint["child_2"] = None

                if new_songs:
                    for song_url in new_songs:
                        file_handle.write(song_url + "\n")
                    file_handle.flush()
                    print(f"  -> Ghi {len(new_songs)} bài hát vào file.")
                else:
                    print("  -> Không tìm thấy bài hát mới cho nghệ sĩ này.")

                time.sleep(RATE_LIMIT_DELAY)


# ---------------- Main ----------------

def main():
    init_checkpoint()
    visited_urls = set()
    completed_parents, checkpoint = load_checkpoint()
    print("Resume từ checkpoint:", checkpoint)
    print("Đã duyệt:", completed_parents)

    seen_urls = set()
    if os.path.exists(OUTPUT_FILE):
        with open(OUTPUT_FILE, "r", encoding="utf-8") as rf:
            for line in rf:
                if line.strip():
                    seen_urls.add(line.strip())

    try:
        with open(OUTPUT_FILE, "a", encoding="utf-8") as f:
            dfs_crawler(SITEMAP_INDEX_URL, visited_urls, f, completed_parents, checkpoint, seen_urls)
            print(f"\n✅ Hoàn tất (hoặc tạm dừng). File: {OUTPUT_FILE}")
    except IOError as e:
        print(f"Lỗi khi ghi file: {e}")

if __name__ == "__main__":
    main()
