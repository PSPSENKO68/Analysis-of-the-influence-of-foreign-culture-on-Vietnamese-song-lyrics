import csv
import requests
from bs4 import BeautifulSoup
import os

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
}

CHECKPOINT_FILE = "checkpoint2.txt"


def fetch_song(url):
    r = requests.get(url, headers=HEADERS, timeout=20)
    if r.status_code != 200:
        print("❌ Error HTTP", r.status_code)
        return None
    soup = BeautifulSoup(r.text, "lxml")

    song_id = url.split("-")[-1]

    title, artist = "", ""
    h1 = soup.find("h1", class_="name_detail")
    if h1:
        full_title = h1.get_text(" ", strip=True)
        if " - " in full_title:
            title, artist = full_title.split(" - ", 1)
        else:
            title = full_title

    a_singer = soup.find("a", class_="singer")
    if a_singer:
        artist = a_singer.get_text(strip=True)

    composer = ""
    composer_tag = soup.select_one("ul.detail-info li p span.label:-soup-contains('Nhạc sĩ:')")
    if composer_tag:
        val = composer_tag.find_next("span", class_="val")
        if val:
            composer = val.get_text(" ", strip=True)

    genre = ""
    genre_tag = soup.select_one("ul.detail-info li p span.label:-soup-contains('Thể loại:')")
    if genre_tag:
        val = genre_tag.find_next("a", class_="val")
        if val:
            genre = val.get_text(strip=True)

    lyrics = ""
    lyric_div = soup.select_one("div.content_lyrics.dsc-body")
    if lyric_div:
        for btn in lyric_div.select("div.btn-exp-coll"):
            btn.decompose()
        for br in lyric_div.find_all("br"):
            br.replace_with("\n")
        lyrics = lyric_div.get_text("\n", strip=True)

    return {
        "id": song_id,
        "title": title,
        "artist": artist,
        "composer": composer,
        "genre": genre,
        "lyrics": lyrics
    }


def get_last_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        with open(CHECKPOINT_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return None


def save_checkpoint(url):
    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as f:
        f.write(url)


if __name__ == "__main__":
    input_file = "all_song_links.txt"
    output_file = "outputNhacvn.csv"

    last_url = get_last_checkpoint()
    skip = bool(last_url)

    with open(output_file, "a", newline="", encoding="utf-8-sig") as csvfile:
        writer = csv.DictWriter(
            csvfile, fieldnames=["id", "title", "artist", "composer", "genre", "lyrics"]
        )

        # nếu file rỗng thì ghi header
        if os.stat(output_file).st_size == 0:
            writer.writeheader()

        with open(input_file, "r", encoding="utf-8") as f:
            for line in f:
                url = line.strip()
                if not url:
                    continue

                # bỏ qua link cho đến khi gặp checkpoint
                if skip:
                    if url == last_url:
                        skip = False
                    continue

                try:
                    song = fetch_song(url)
                    if song:
                        writer.writerow(song)
                        save_checkpoint(url)  # lưu checkpoint ngay
                        print(f"✔ {song['title']} - {song['artist']}")
                except Exception as e:
                    print(f"❌ Error with {url}: {e}")

    print("✅ Done, dữ liệu đã được lưu vào CSV.")
