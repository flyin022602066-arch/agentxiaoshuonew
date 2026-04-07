# ==========================================
# 多 Agent 协作小说系统 - Celery App 导出
# ==========================================

"""统一导出 Celery app，避免循环导入。"""

from app.tasks.agent_tasks import celery_app

__all__ = ["celery_app"]
