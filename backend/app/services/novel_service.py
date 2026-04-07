from typing import Any, Dict, List

from app.novel_db import get_novel_database
from app.services.chapter_service import get_chapter_service


class NovelService:
    def __init__(self):
        self.db = get_novel_database()
        self.chapter_service = get_chapter_service()

    def list_novels(self) -> List[Dict[str, Any]]:
        return self.db.get_all_novels()

    def create_novel(self, novel_data: Dict[str, Any]) -> Dict[str, Any]:
        title = novel_data.get("title", "")
        if not title:
            raise ValueError("小说标题不能为空")
        settings = novel_data.get("settings") or {}
        novel_id = self.db.create_novel(
            title=title,
            genre=novel_data.get("genre", "fantasy"),
            description=novel_data.get("description", ""),
            author=novel_data.get("author", "AI Author"),
            settings=settings,
        )
        return {"novel_id": novel_id, "title": title, "settings": settings}

    def get_novel(self, novel_id: str) -> Dict[str, Any] | None:
        novel = self.db.get_novel(novel_id)
        if not novel:
            return None
        return {**novel, "stats": self.db.get_novel_stats(novel_id)}

    def update_novel(self, novel_id: str, novel_data: Dict[str, Any]) -> bool:
        if not self.db.get_novel(novel_id):
            return False
        self.db.update_novel(novel_id, **novel_data)
        return True

    def delete_novel(self, novel_id: str) -> None:
        self.db.delete_novel(novel_id)

    def list_characters(self, novel_id: str) -> List[Dict[str, Any]]:
        return self.db.get_characters(novel_id)

    def add_character(self, novel_id: str, character_data: Dict[str, Any]) -> Dict[str, Any]:
        name = character_data.get("name", "")
        if not name:
            raise ValueError("人物名称不能为空")
        character_id = self.db.add_character(
            novel_id,
            name=name,
            role=character_data.get("role", ""),
            description=character_data.get("description", ""),
            traits=character_data.get("traits", []),
        )
        return {"character_id": character_id, "name": name}

    def list_hooks(self, novel_id: str) -> List[Dict[str, Any]]:
        return self.db.get_unresolved_hooks(novel_id)


_novel_service: NovelService | None = None


def get_novel_service() -> NovelService:
    global _novel_service
    if _novel_service is None:
        _novel_service = NovelService()
    return _novel_service
