import json
import sqlite3
import sys
from difflib import SequenceMatcher


def normalize_text(text: str, max_chars: int = 1800) -> str:
    return "".join((text or "").split())[:max_chars]


def main(novel_id: str):
    conn = sqlite3.connect("data/novels.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        "select chapter_num, title, word_count, status, content from chapters where novel_id = ? order by chapter_num asc",
        (novel_id,),
    )
    rows = [dict(row) for row in cursor.fetchall()]
    prev_content = None
    report = []
    for row in rows:
        content = row.get("content") or ""
        similarity = None
        if prev_content and content:
            similarity = round(
                SequenceMatcher(None, normalize_text(prev_content), normalize_text(content)).ratio(),
                3,
            )
        report.append(
            {
                "chapter_num": row["chapter_num"],
                "title": row.get("title"),
                "word_count": row.get("word_count"),
                "status": row.get("status"),
                "similarity_to_prev": similarity,
                "preview": content[:200],
            }
        )
        prev_content = content

    print(json.dumps(report, ensure_ascii=False, indent=2))
    conn.close()


if __name__ == "__main__":
    main(sys.argv[1])
