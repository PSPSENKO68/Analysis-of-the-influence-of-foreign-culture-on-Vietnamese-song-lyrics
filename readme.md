# Vietnamese Lyrics Classification System

A comprehensive pipeline for collecting, standardizing, and automatically classifying language patterns in Vietnamese song lyrics.

---

## 🚀 Quick Start

### Installation

```bash
pip install pandas numpy nltk requests groq beautifulsoup4 scikit-learn
pip install unidecode fuzzywuzzy matplotlib seaborn
```

### NLTK Setup

```python
python -c "import nltk; nltk.download('words')"
```

### API Requirements

- **Groq API** (free tier with rate limits)

---

## 📁 Project Structure

```
NguyenQuocBinh_52200275_52200209/
│
├── Source/
│   ├── Data_Crawler/
│   │   ├── tkaraoke/
│   │   │   ├── tkaraoke.py
│   │   │   ├── converter.py
│   │   │   ├── tkaraoke.db
│   │   │   ├── tkaraoke_full_metadata.csv
│   │   │   └── tkaraoke_output.csv
│   │   │
│   │   └── nhacvn/
│   │       ├── nhacvnLinkSongCrawler.py
│   │       ├── oneSongDataCrawler.py
│   │       ├── all_song_links.txt
│   │       ├── checkpoint.txt
│   │       ├── checkpoint2.txt
│   │       └── outputNhacvn.csv
│   │
│   ├── Data_Standardized/
│   │   ├── tkaraoke_nhacvn_standardized/
│   │   ├── merge_data/
│   │   ├── yearFiller/
│   │   └── nhacvn_refill_urls/
│   │
│   └── Calculate_and_Analysis/
│       ├── chia_output/
│       ├── Local_AI/
│       ├── build_HanViet_dic/
│       ├── thuvien/
│       ├── Calculate_Analysis/
│       └── analysis/
│
└── README.md
```

---

## 🎯 Overview

**Pipeline:** Crawl → Standardize → Label → Analyze

This system processes Vietnamese song lyrics through multiple stages to classify language usage patterns including Vietnamese, Sino-Vietnamese (Hán Việt), English, and foreign transliterations.

---

## 📊 Part I: Data Collection & Standardization

### 1. Data Crawling

#### A. TKaraoke Source (`/tkaraoke/`)
- `tkaraoke.py` → generates `tkaraoke.db` + metadata
- `converter.py` → produces `tkaraoke_output.csv`

#### B. NhacVN Source (`/nhacvn/`)
- `nhacvnLinkSongCrawler.py` → collects links to `all_song_links.txt`
- `oneSongDataCrawler.py` → extracts data to `outputNhacvn.csv`

### 2. Data Standardization (`/tkaraoke_nhacvn_standardized/`)

**Notebook:** `Processing.ipynb`

Normalizes all sources to common schema:
```
{title, composers, lyricists, year, genres, lyrics, urls, source, note}
```

### 3. Merging Sources (`/merge_data/`)

Combines 6 data sources with deduplication:
- **Duplicate Detection:** Title + Composer matching
- **Lyrics Similarity:** 70% threshold
- **Output:** `merged_final_lyric.csv`

### 4. Year Filling (`/yearFiller/`)

Enriches dataset with release years using:
- MusicBrainz API
- Wikipedia
- iTunes API

**Output:** `dataset_with_year.csv`

### 5. URL Refilling (`/nhacvn_refill_urls/`)

Recovers missing URLs using:
- Fuzzy matching with TF-IDF
- Threshold: 0.75

**Final Output:** `final_dataset_cleaned_v3.csv`

---

## 🏷️ Part II: Classification & Labeling

**Input:** `final_dataset_cleaned_v3.csv`

### 1. LLM Classification (`/chia_output/`)

**Notebook:** `lyrics_classification.ipynb`

- **Models:** Groq API (llama-3.1, qwen3)
- **Accuracy:** 70-80%
- **Purpose:** Initial rough classification

### 2. Building Sino-Vietnamese Dictionary (`/build_HanViet_dic/`)

**Notebook:** `build.ipynb`

Combines 2 GitHub sources → `hanviet.csv`

### 3. Dictionary Cleaning (`/thuvien/`)

**Notebook:** `minus.ipynb`

Removes conflicts between 6 dictionaries:
- `teencode.csv` - Internet slang
- `noise.csv` - Non-linguistic tokens
- `ten_rieng.csv` - Proper nouns
- `english.csv` - English words
- `hanviet.csv` - Sino-Vietnamese
- `phien_am.csv` - Foreign transliterations

**Constraint:** Ensures `english ∩ ten_rieng ∩ phien_am = ∅`

### 4. Token Labeling (`/Calculate_Analysis/`)

**Notebook:** `calculate.ipynb`

#### 5-Step Pipeline:

**STEP 1: Text Normalization**
- Unicode normalization
- Fix confusable characters
- Remove noise
- Expand teencode
- Normalize whitespace

**STEP 2: Noise Removal**
- Classify word/phrase noise
- Regex-based removal

**STEP 3A-E: Priority-Based Labeling**

| Step | Category | Type | Matching |
|------|----------|------|----------|
| 3A | `FOREIGN_*` | Transliteration | Multi-word, case-insensitive |
| 3B | `PROPER_NOUN` | Named entities | Case-sensitive, max 5 words |
| 3C | `HANVIET` | Sino-Vietnamese | Single word |
| 3D | `VIETNAMESE` | Pure Vietnamese | Single word (Viet74K) |
| 3E | `ENGLISH` | English | Single word (NLTK + custom) |

**Output:** `final_dataset_complete.csv`

**Output Columns:**
- `labeled_tokens` - All token labels
- `phien_am_*` - Foreign transliteration stats
- `proper_nouns` - Named entities
- `hanviet_words` - Sino-Vietnamese words
- `vietnamese_words` - Pure Vietnamese words
- `english_words` - English words
- `num_unlabeled` - Unclassified tokens

---

## 📈 Part III: Statistical Analysis

**Notebook:** `analysis.ipynb` (`/Calculate_Analysis/`)

**Input:** `final_dataset_with_period.csv`

### 7 Key Analyses

#### 1. Language Distribution by Period (1990-2025)
- **Chart:** 100% stacked bar
- **Categories:** Vietnamese | Sino-Vietnamese | English | Other Foreign

#### 2. Non-Vietnamese Language Breakdown
- **Chart:** Normalized 100% composition
- **Categories:** Sino-Vietnamese | English | Transliteration (Korean/Japanese/Chinese)

#### 3. English Usage Trends Over Time
- **Chart:** Line chart
- **Metrics:** 
  - Raw percentage of songs with English
  - 3-year rolling average

#### 4. English Usage by Genre
- **Chart:** Bar chart
- **Scope:** Top 15 genres (≥200 songs)

#### 5. English Usage by Composer
- **Chart:** Bar chart
- **Scope:** Top 15 composers (≥200 songs)

#### 6. Transliteration Popularity
- **Chart:** Bar chart
- **Languages:** Korean > English > Japanese > Chinese

#### 7. Transliteration Trends by Period
- **Chart:** Multi-line chart
- **Languages:** 8 foreign languages over time

### 🔍 Key Findings

- ✅ Vietnamese usage declining, English increasing sharply after 2015
- ✅ Korean transliteration surge 2015-2020 (Hallyu Wave effect)
- ✅ **Rap/Hip-hop:** 80% contain English words
- ✅ **Ballad:** 30% contain English words

---

## 📝 Schema Reference

### Common Data Schema
```python
{
    "title": str,
    "composers": str,
    "lyricists": str,
    "year": int,
    "genres": str,
    "lyrics": str,
    "urls": str,
    "source": str,
    "note": str
}
```

### Label Categories
- `VIETNAMESE` - Pure Vietnamese words
- `HANVIET` - Sino-Vietnamese words
- `ENGLISH` - English words
- `PROPER_NOUN` - Named entities
- `FOREIGN_KOREAN` - Korean transliterations
- `FOREIGN_JAPANESE` - Japanese transliterations
- `FOREIGN_CHINESE` - Chinese transliterations
- `FOREIGN_OTHER` - Other foreign transliterations

---

## 📅 Version History

**Last Updated:** January 7, 2025

---

## 👥 Contributors

- Nguyen Quoc Binh - 52200275
- [Collaborator] - 52200209

---

## 📄 License

[Add your license information here]

---

## 🤝 Contributing

[Add contribution guidelines here]

---

## 📧 Contact

[Add contact information here]
