import json
import sqlite3


def main():
    conn = sqlite3.connect("data/novels.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "select id, title, total_chapters, total_words, updated_at from novels order by updated_at desc limit 10"
    )
    rows = [dict(row) for row in cursor.fetchall()]
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    conn.close()


if __name__ == "__main__":
    main()
