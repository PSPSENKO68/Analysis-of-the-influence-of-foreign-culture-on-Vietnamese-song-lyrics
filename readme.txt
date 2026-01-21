=============================================================================
README - HỆ THỐNG PHÂN LOẠI LYRICS TIẾNG VIỆT
=============================================================================
YÊU CẦU
=============================================================================

Cài đặt:
pip install pandas numpy nltk requests groq beautifulsoup4 scikit-learn
pip install unidecode fuzzywuzzy matplotlib seaborn

NLTK:
python -c "import nltk; nltk.download('words')"

API: Groq (miễn phí, rate limit)

=============================================================================
CẤU TRÚC THƯ MỤC ĐẦY ĐỦ
=============================================================================

NguyenQuocBinh_52200275_52200209/
│
├── Source/
│   │
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
│   │   │   ├── Processing.ipynb
│   │   │   ├── normalize_Nhacvn_output.csv
│   │   │   ├── normalize_tkaraoke_output.csv
│   │   │   ├── refill_lyricists_nhacvn.csv
│   │   │   ├── refill_lyricists_tkaraoke.csv
│   │   │   ├── filled_source_nhacvn.csv
│   │   │   └── filled_source_tkaraoke.csv
│   │   │
│   │   ├── merge_data/
│   │   │   ├── merge.ipynb
│   │   │   ├── N01_hopamviet_final.csv
│   │   │   ├── N02_timbaihat_final.csv
│   │   │   ├── N03_loibaihat_final.csv
│   │   │   ├── N04_nhacvn_final.csv
│   │   │   ├── N04_tkaraoke_final.csv
│   │   │   ├── N05_timbaihat_final.csv
│   │   │   ├── merged_final.csv
│   │   │   └── merged_final_lyric.csv
│   │   │
│   │   ├── yearFiller/
│   │   │   ├── yearFiller.ipynb
│   │   │   ├── year_filler.log
│   │   │   └── dataset_with_year.csv
│   │   │
│   │   └── nhacvn_refill_urls/
│   │       ├── refill_urls.ipynb
│   │       ├── final_dataset_no_nhacvn.csv
│   │       ├── preview_replace_title_comp_lyrics.csv
│   │       ├── final_dataset_filled.csv
│   │       └── final_dataset_cleaned_v3.csv
│   │
│   └── Calculate_and_Analysis/
│       ├── chia_output/
│       │   ├── lyrics_classification.ipynb
│       │   ├── output_labeling_part1.csv
│       │   ├── output_labeling_part2.csv
│       │   ├── output_labeling_part3.csv
│       │   └── output_labeling_part4.csv
│       │
│       ├── Local_AI/
│       │   └── word_classify_LLM.ipynb
│       │
│       ├── build_HanViet_dic/
│       │   ├── build.ipynb
│       │   ├── chinese-hanviet-cognates.tsv
│       │   ├── hanviet.csv
│       │   ├── CVDICT.u8
│       │   └── hanviet_dictionary.csv
│       │
│       ├── thuvien/
│       │   ├── minus.ipynb
│       │   ├── teencode.csv
│       │   ├── noise.csv
│       │   ├── ten_rieng.csv
│       │   ├── ten_rieng_no_common.csv
│       │   ├── english.csv
│       │   ├── english_cleaned.csv
│       │   ├── english_really_final.csv
│       │   ├── hanviet.csv
│       │   ├── han_viet_filtered.csv
│       │   ├── hanviet_dictionary.csv
│       │   ├── phien_am.csv
│       │   ├── phien_am_cleaned.csv
│       │   ├── vietnamese.csv
│       │   └── thuvien.csv
│       │
│       ├── Calculate_Analysis/
│       │   ├── calculate.ipynb
│       │   ├── final_dataset_step1_teencode.csv
│       │   ├── final_dataset_step2_noise.csv
│       │   ├── final_dataset_step3a_phienam.csv
│       │   ├── final_dataset_step3b_proper_noun.csv
│       │   ├── final_dataset_step3c_hanviet.csv
│       │   ├── final_dataset_step3d_vietnamese.csv
│       │   ├── final_dataset_step3e_english.csv
│       │   ├── final_dataset_complete.csv
│       │   ├── final_dataset_with_period.csv
│       │   ├── step3a_phienam_conflicts.csv
│       │   ├── step3b_proper_noun_conflicts.csv
│       │   └── label_conflicts.csv
│       │
│       └── analysis/
│           └── analysis.ipynb
│
└── README.txt

=============================================================================
TỔNG QUAN
=============================================================================
Thu thập, chuẩn hóa và phân loại tự động ngôn ngữ trong lyrics Việt
Pipeline: Crawl → Chuẩn hóa → Gán nhãn → Phân tích


=============================================================================
I. THU THẬP & CHUẨN HÓA
=============================================================================

1. CRAWL DỮ LIỆU
----------------
A. TKaraoke (/tkaraoke/)
   tkaraoke.py → tkaraoke.db + metadata.csv
   converter.py → tkaraoke_output.csv

B. NhacVN (/nhacvn/)
   nhacvnLinkSongCrawler.py → all_song_links.txt
   oneSongDataCrawler.py → outputNhacvn.csv

2. CHUẨN HÓA (/tkaraoke_nhacvn_standardized/)
----------------------------------------------
Processing.ipynb: Chuẩn hóa về schema chung
{title, composers, lyricists, year, genres, lyrics, urls, source, note}

3. GỘP NGUỒN (/merge_data/)
---------------------------
Gộp 6 nguồn → loại trùng (title+composer, lyrics similarity 70%)
Output: merged_final_lyric.csv

4. ĐIỀN YEAR (/yearFiller/)
---------------------------
Truy vấn: MusicBrainz → Wikipedia → iTunes

5. REFILL URLs (/nhacvn_refill_urls/)
-------------------------------------
Fuzzy matching (TF-IDF, threshold 0.75) → khôi phục URLs
Output: final_dataset_cleaned_v3.csv


=============================================================================
II. PHÂN LOẠI & GÁN NHÃN
=============================================================================

INPUT: final_dataset_cleaned_v3.csv

1. LLM PHÂN LOẠI (/chia_output/)
--------------------------------
lyrics_classification.ipynb
Groq API (llama-3.1, qwen3) → phân loại sơ bộ
Độ chính xác: 70-80%

2. BUILD TỪ ĐIỂN HÁN VIỆT (/build_HanViet_dic/)
------------------------------------------------
build.ipynb: Gộp 2 nguồn GitHub → hanviet.csv

3. LÀM SẠCH THƯ VIỆN (/thuvien/)
--------------------------------
minus.ipynb: Loại xung đột giữa 6 từ điển
- teencode.csv, noise.csv
- ten_rieng.csv, english.csv
- hanviet.csv, phien_am.csv
Đảm bảo: english ∩ ten_rieng ∩ phien_am = ∅

4. GÁN NHÃN (/Calculate_Analysis/)
----------------------------------
calculate.ipynb - Pipeline 5 bước:

STEP 1: Chuẩn hóa văn bản
  Unicode normalize → fix confusable → remove noise → teencode → whitespace

STEP 2: Loại noise
  Phân loại word/phrase noise → regex remove

STEP 3A-E: Gán nhãn theo thứ tự ưu tiên
  3A. FOREIGN_* (phiên âm) - multi-word, case-insensitive
  3B. PROPER_NOUN (tên riêng) - case-sensitive, max 5 words
  3C. HANVIET (Hán Việt) - single word
  3D. VIETNAMESE (Viet74K) - single word
  3E. ENGLISH (NLTK + custom) - single word

OUTPUT: final_dataset_complete.csv
Cột: labeled_tokens | phien_am_* | proper_nouns | hanviet_words | 
     vietnamese_words | english_words | num_unlabeled


=============================================================================
III. PHÂN TÍCH THỐNG KÊ
=============================================================================

analysis.ipynb (/Calculate_Analysis/)

INPUT: final_dataset_with_period.csv

7 PHÂN TÍCH CHÍNH:

1. Tỷ lệ ngôn ngữ theo giai đoạn (1990-2025)
   Stacked bar 100%: Việt | Hán Việt | Anh | Ngoại ngữ khác

2. Cơ cấu phần "không phải tiếng Việt"
   Chuẩn hóa 100%: Hán Việt | Anh | Phiên âm (Korea/Japan/China)

3. Xu hướng tiếng Anh theo năm
   Line chart: Tỷ lệ bài có tiếng Anh (raw + rolling 3-year)

4. Tiếng Anh theo thể loại
   Bar chart: Top 15 genres (≥200 bài)

5. Tiếng Anh theo nhạc sĩ
   Bar chart: Top 15 composers (≥200 bài)

6. Mức độ phổ biến phiên âm
   Bar chart: Số bài theo ngôn ngữ (Korea > English > Japan > China)

7. Xu hướng phiên âm theo giai đoạn
   Multi-line chart: 8 ngôn ngữ qua thời gian

PHÁT HIỆN CHÍNH:
- Tiếng Việt giảm, Anh tăng mạnh sau 2015
- Phiên âm Korea tăng đột biến 2015-2020 (Hallyu)
- Rap/Hip-hop: 80% có tiếng Anh, Ballad: 30%


=============================================================================
Cập nhật: 2025-01-07
=============================================================================
