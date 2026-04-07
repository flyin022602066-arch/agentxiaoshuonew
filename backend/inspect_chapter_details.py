import json
import sqlite3
import sys


def main(novel_id: str):
    conn = sqlite3.connect("data/novels.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "select chapter_num, title, outline, substr(content,1,800) as preview from chapters where novel_id = ? order by chapter_num asc",
        (novel_id,),
    )
    rows = [dict(row) for row in cursor.fetchall()]
    print(json.dumps(rows, ensure_ascii=False, indent=2))
    conn.close()


if __name__ == "__main__":
    main(sys.argv[1])
