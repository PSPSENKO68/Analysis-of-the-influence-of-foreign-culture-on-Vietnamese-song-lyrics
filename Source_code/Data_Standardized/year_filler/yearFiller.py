import pandas as pd
import requests
import time
import re
import logging
from tqdm import tqdm
from datetime import datetime
import os

# ==================== LOGGING CONFIG ====================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)
start_time = datetime.now()
logger.info("=== Bắt đầu điền cột 'year' sử dụng MusicBrainz + Wikipedia + iTunes ===")

# ==================== FILE I/O ====================
input_file = "l3/nhacvn.csv"
output_file = "yearFiller/yearFiller_nhacvn_output.csv"
checkpoint_file = "yearFiller/checkpoint_years.csv"

# Đọc dữ liệu
try:
    df = pd.read_csv(input_file, encoding="utf-8-sig")
    df.columns = df.columns.str.strip().str.lower()
    logger.info(f"Đã đọc {len(df)} hàng từ file: {input_file}")
except Exception as e:
    logger.error(f"Lỗi khi đọc file CSV: {e}")
    raise SystemExit(e)

# Đảm bảo các cột cần thiết tồn tại
for col in ["year", "note"]:
    if col not in df.columns:
        df[col] = ""
df["note"] = df["note"].astype(str)

# ==================== HÀM 1: MusicBrainz ====================
def get_song_year_musicbrainz(title, artist=None):
    try:
        query = title
        if artist:
            query += f" AND artist:{artist}"

        url = f"https://musicbrainz.org/ws/2/recording/?query={query}&fmt=json&limit=1"
        headers = {"User-Agent": "NhacVN-YearFiller/1.0 (example@gmail.com)"}
        r = requests.get(url, headers=headers, timeout=15)
        r.raise_for_status()
        data = r.json()

        recordings = data.get("recordings", [])
        if not recordings:
            return None

        rec = recordings[0]
        releases = rec.get("releases", [])
        if not releases:
            return None

        date = releases[0].get("date", "")
        if not date:
            return None

        match = re.search(r"\b(19|20)\d{2}\b", date)
        if match:
            return int(match.group(0))
        return None
    except Exception as e:
        logger.warning(f"[MusicBrainz] Lỗi truy vấn {title}: {e}")
        return None

# ==================== HÀM 2: Wikipedia (có User-Agent và fallback) ====================
def get_song_year_wikipedia(title):
    try:
        headers = {
            "User-Agent": "NhacVN-YearFiller/1.0 (https://github.com/duynguyen or contact@example.com)"
        }

        base_urls = [
            "https://vi.wikipedia.org/w/api.php",
            "https://en.wikipedia.org/w/api.php",  # fallback nếu tiếng Việt bị chặn
        ]

        for base_url in base_urls:
            params = {
                "action": "query",
                "list": "search",
                "srsearch": title,
                "format": "json",
                "utf8": 1,
                "srlimit": 1,
            }
            r = requests.get(base_url, params=params, headers=headers, timeout=15)
            if r.status_code == 403:
                logger.warning(f"[Wikipedia] {base_url} bị chặn, thử fallback khác...")
                continue

            r.raise_for_status()
            data = r.json()
            search_results = data.get("query", {}).get("search", [])
            if not search_results:
                continue

            page_title = search_results[0]["title"]

            extract_url = f"{base_url.replace('/w/api.php', '')}/api/rest_v1/page/summary/{page_title}"
            r = requests.get(extract_url, headers=headers, timeout=10)
            if r.status_code == 403:
                logger.warning(f"[Wikipedia Summary] {base_url} bị chặn, bỏ qua.")
                continue
            r.raise_for_status()
            summary_data = r.json()
            extract = summary_data.get("extract", "")

            match = re.search(r"\b(19|20)\d{2}\b", extract)
            if match:
                return int(match.group(0))

        return None
    except Exception as e:
        logger.warning(f"[Wikipedia] Lỗi truy vấn {title}: {e}")
        return None


# ==================== HÀM 3: iTunes (Apple Music) ====================
def get_song_year_itunes(title, artist=None):
    try:
        query = title
        if artist:
            query += f" {artist}"
        url = f"https://itunes.apple.com/search"
        params = {"term": query, "entity": "song", "limit": 1, "country": "us"}
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()

        results = data.get("results", [])
        if not results:
            return None

        release_date = results[0].get("releaseDate", "")
        if not release_date:
            return None

        match = re.search(r"\b(19|20)\d{2}\b", release_date)
        if match:
            return int(match.group(0))
        return None
    except Exception as e:
        logger.warning(f"[iTunes] Lỗi truy vấn {title}: {e}")
        return None

# ==================== QUY TRÌNH FILL DỮ LIỆU ====================
need_fill = df["year"].isna() | (df["year"].astype(str).str.strip() == "")
indices = df[need_fill].index.tolist()
logger.info(f"Cần điền 'year' cho {len(indices)} bài hát")

for idx in tqdm(indices, desc="Filling year"):
    title = df.loc[idx, "title"]
    artist = None
    if "composers" in df.columns and isinstance(df.loc[idx, "composers"], str):
        artist = df.loc[idx, "composers"].split(",")[0]

    # --- Ưu tiên 1: MusicBrainz ---
    year = get_song_year_musicbrainz(title, artist)
    source = "MusicBrainz"

    # --- Ưu tiên 2: Wikipedia ---
    if not year:
        time.sleep(0.4)
        year = get_song_year_wikipedia(title)
        source = "Wikipedia" if year else None

    # --- Ưu tiên 3: iTunes ---
    if not year:
        time.sleep(0.4)
        year = get_song_year_itunes(title, artist)
        source = "iTunes" if year else None

    # --- Cập nhật kết quả ---
    if year:
        df.loc[idx, "year"] = year
        df.loc[idx, "note"] = f"đã fill 'year' sử dụng {source}"
    else:
        df.loc[idx, "note"] = "không tìm thấy thông tin năm phát hành"

    # --- Ghi checkpoint mỗi 10 dòng ---
    if (idx + 1) % 10 == 0:
        df.to_csv(checkpoint_file, index=False, encoding="utf-8-sig")

    # --- Giới hạn tốc độ ---
    time.sleep(1.0)

# ==================== GHI FILE CUỐI ====================
df.to_csv(output_file, index=False, encoding="utf-8-sig")
logger.info(f"✅ Đã ghi file kết quả: {output_file}")

if os.path.exists(checkpoint_file):
    os.remove(checkpoint_file)
    logger.info("🗑️ Đã xóa checkpoint file")

elapsed = datetime.now() - start_time
logger.info(f"⏱️ Thời gian chạy: {elapsed}")
logger.info("=== Hoàn tất điền cột 'year' (MusicBrainz + Wikipedia + iTunes) ===")
