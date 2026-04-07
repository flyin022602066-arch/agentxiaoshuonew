from fastapi import APIRouter, HTTPException
from typing import Any, Dict
import logging
import asyncio

from app.api.responses import error_response, success_response
from app.services.auto_service import get_auto_service
from app.tasks.task_manager import get_task_manager, generate_task_id, TaskStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["全自动创作"])


@router.post("/auto/create")
async def auto_create_novel(data: Dict[str, Any]):
    try:
        title = data.get("title", "")
        if not title:
            raise ValueError("小说标题不能为空")

        task_id = generate_task_id("auto")
        get_task_manager().create_task(
            task_id=task_id,
            task_type="auto_creation",
            metadata={
                "title": title,
                "genre": data.get("genre", ""),
                "chapter_count": data.get("chapter_count", 3000),
            }
        )

        asyncio.create_task(_execute_auto_creation(task_id, data))

        return success_response({
            "task_id": task_id,
            "status": "pending",
            "message": "全自动创作任务已提交，请轮询 /api/auto/task/{task_id} 查看进度"
        })
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"全自动创作失败：{e}")
        logger.error(str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def _execute_auto_creation(task_id: str, data: Dict[str, Any]):
    task_manager = get_task_manager()
    title = data.get("title", "")

    try:
        task_manager.update_task(task_id, status=TaskStatus.RUNNING, progress=5, current_stage="开始创建蓝图")
        result = await get_auto_service().create_novel(data, task_id=task_id)

        if result.get("status") == "success":
            task_manager.update_task(
                task_id,
                status=TaskStatus.COMPLETED,
                progress=100,
                current_stage="全自动创作完成",
                result={
                    "novel_id": result.get("novel_id"),
                    "blueprint": result.get("blueprint"),
                    "first_chapter": result.get("first_chapter"),
                    "title": title,
                }
            )
            return

        message = result.get("error") or result.get("message") or result.get("first_chapter", {}).get("message") or "创作失败"
        task_manager.update_task(
            task_id,
            status=TaskStatus.FAILED,
            current_stage="全自动创作失败",
            error=message,
            result=result,
        )
    except Exception as e:
        logger.error(f"全自动创作任务 {task_id} 失败：{e}", exc_info=True)
        task_manager.update_task(
            task_id,
            status=TaskStatus.FAILED,
            current_stage="全自动创作失败",
            error=str(e) or e.__class__.__name__,
        )


@router.get("/auto/task/{task_id}")
async def get_auto_create_task_status(task_id: str):
    task = get_task_manager().get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"任务不存在：{task_id}")

    return success_response(task.to_dict())


@router.get("/auto/blueprint/{novel_id}")
async def get_novel_blueprint(novel_id: str):
    try:
        result = get_auto_service().get_blueprint(novel_id)
        if not result:
            raise HTTPException(status_code=404, detail="小说不存在")
        return success_response(result)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取蓝图失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))
