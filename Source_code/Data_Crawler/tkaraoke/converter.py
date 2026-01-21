import sqlite3
import csv

def export_to_csv(db_path="tkaraoke.db", table="urls", csv_path="tkaraoke_output.csv"):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Lấy toàn bộ dữ liệu
    cur.execute(f"SELECT * FROM {table}")
    rows = cur.fetchall()

    # Lấy tên cột
    col_names = [desc[0] for desc in cur.description]

    # Ghi ra CSV với UTF-8 BOM (Excel đọc được tiếng Việt)
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=",")
        writer.writerow(col_names)  # header

        # lọc bỏ các dòng chứa "no content"
        count = 0
        for row in rows:
            # nếu bất kỳ cột nào chứa "no content" thì bỏ qua
            if any(isinstance(col, str) and "no_content" in col.lower() for col in row):
                continue
            writer.writerow(row)
            count += 1

    conn.close()
    print(f"✅ Xuất thành công {count} dòng (đã lọc) ra file: {csv_path}")

if __name__ == "__main__":
    export_to_csv("tkaraoke.db", "urls", "tkaraoke_output.csv")
