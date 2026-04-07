from pathlib import Path
from typing import Any, Dict, List, Optional

from app.novel_db import NovelDatabase


class ChapterService:
    def __init__(self, db_path: str | Path | None = None):
        self.db = NovelDatabase(str(db_path) if db_path else None)

    def create_novel(self, title: str, genre: str = "fantasy", description: str = "", author: str = "AI Author") -> str:
        return self.db.create_novel(title=title, genre=genre, description=description, author=author)

    def list_chapters(self, novel_id: str) -> List[Dict[str, Any]]:
        return self.db.get_all_chapters(novel_id)

    def get_chapter(self, novel_id: str, chapter_num: int) -> Optional[Dict[str, Any]]:
        return self.db.get_chapter(novel_id, chapter_num)

    def create_chapter(self, novel_id: str, chapter_num: int, title: str = "", outline: str = "") -> int:
        existing = self.db.get_chapter(novel_id, chapter_num)
        if existing:
            return existing["id"]
        return self.db.create_chapter(novel_id, chapter_num, title, outline)

    def save_chapter(
        self,
        novel_id: str,
        chapter_num: int,
        title: str = "",
        outline: str = "",
        content: str = "",
        status: str = "draft",
    ) -> Dict[str, Any]:
        self.create_chapter(novel_id, chapter_num, title=title, outline=outline)
        self.db.update_chapter(
            novel_id,
            chapter_num,
            content=content,
            title=title,
            outline=outline,
            status=status,
        )
        return self.db.get_chapter(novel_id, chapter_num)

    def delete_chapter(self, novel_id: str, chapter_num: int) -> bool:
        return self.db.delete_chapter(novel_id, chapter_num)


_chapter_service: ChapterService | None = None


def get_chapter_service() -> ChapterService:
    global _chapter_service
    if _chapter_service is None:
        _chapter_service = ChapterService()
    return _chapter_service
