from typing import Any, Dict


class AutoService:
    async def create_novel(self, data: Dict[str, Any], task_id: str = None):
        from app.novel_architect import get_auto_creation_system
        from app.tasks.task_manager import get_task_manager

        title = data.get("title", "")
        if not title:
            raise ValueError("小说标题不能为空")

        def _progress(progress: int, stage: str):
            if not task_id:
                return
            try:
                normalized_progress = max(0, min(progress, 99)) if progress < 100 else 100
                get_task_manager().update_task(task_id, status=None, progress=normalized_progress, current_stage=stage)
            except Exception:
                pass

        _progress(10, "正在生成世界观")
        system = get_auto_creation_system()
        return await system.create_novel_from_scratch(
            title,
            data.get("genre", ""),
            data.get("description", ""),
            data.get("chapter_count", 3000),
            data.get("auto_style", {}),
            progress_callback=_progress,
        )

    def get_blueprint(self, novel_id: str):
        from app.novel_db import get_novel_database

        db = get_novel_database()
        novel = db.get_novel(novel_id)
        if not novel:
            return None
        return {"novel": novel, "stats": db.get_novel_stats(novel_id)}


_auto_service: AutoService | None = None


def get_auto_service() -> AutoService:
    global _auto_service
    if _auto_service is None:
        _auto_service = AutoService()
    return _auto_service
