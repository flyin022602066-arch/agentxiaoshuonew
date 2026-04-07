from fastapi import APIRouter, HTTPException
from typing import Any, Dict
import logging

from app.services.writing_service import get_writing_service
from app.api.responses import error_response, success_response
from app.tasks.task_manager import get_task_manager, generate_task_id, TaskStatus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["写作流程"])


@router.post("/writing/chapter", name="create_writing_chapter")
async def create_writing_chapter(chapter_data: Dict[str, Any]):
    """提交章节创作任务，返回 task_id 用于轮询进度"""
    try:
        task_id = generate_task_id("chapter")
        novel_id = chapter_data.get("novel_id", "default")
        chapter_num = chapter_data.get("chapter_num", 1)
        
        task_manager = get_task_manager()
        task_manager.create_task(
            task_id=task_id,
            task_type="chapter_creation",
            metadata={
                "novel_id": novel_id,
                "chapter_num": chapter_num,
                "outline": chapter_data.get("outline", "")[:100]
            }
        )
        
        # 异步执行创作（不阻塞返回）
        import asyncio
        asyncio.create_task(_execute_chapter_creation(task_id, chapter_data))
        
        return success_response({
            "task_id": task_id,
            "status": "pending",
            "message": "章节创作任务已提交，请轮询 /api/writing/task/{task_id} 查看进度"
        })
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"提交章节创作失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _execute_chapter_creation(task_id: str, chapter_data: Dict[str, Any]):
    """后台执行章节创作，更新任务进度"""
    task_manager = get_task_manager()
    try:
        task_manager.update_task(task_id, status=TaskStatus.RUNNING, progress=0, current_stage="开始创作")
        
        # 传入 task_id 让 service 能更新进度
        result = await get_writing_service().create_chapter_workflow(chapter_data, task_id=task_id)
        
        if result["status"] == "success":
            task_manager.update_task(
                task_id,
                status=TaskStatus.COMPLETED,
                progress=100,
                current_stage="创作完成",
                result={
                    "workflow_id": result.get("workflow_id"),
                    "chapter_num": result.get("chapter_num"),
                    "word_count": result.get("word_count"),
                    "content": result.get("content", "")
                }
            )
        else:
            error_msg = result.get("message", "未知错误")
            logger.error(f"工作流返回错误：{error_msg}")
            task_manager.update_task(
                task_id,
                status=TaskStatus.FAILED,
                progress=0,
                current_stage="创作失败",
                error=error_msg
            )
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        logger.error(f"任务 {task_id} 执行失败：{e}\n{error_detail}")
        task_manager.update_task(
            task_id,
            status=TaskStatus.FAILED,
            error=f"{str(e)}\n\n详细日志请查看后端控制台"
        )


@router.get("/writing/task/{task_id}")
async def get_writing_task_status(task_id: str):
    """轮询章节创作任务进度"""
    task_manager = get_task_manager()
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"任务不存在：{task_id}")
    
    return success_response({
        "task_id": task.task_id,
        "status": task.status.value if isinstance(task.status, TaskStatus) else task.status,
        "progress": task.progress,
        "current_stage": task.current_stage,
        "result": task.result,
        "error": task.error,
        "created_at": task.created_at.isoformat() if task.created_at else None,
        "updated_at": task.updated_at.isoformat() if task.updated_at else None,
    })


@router.get("/writing/chapter/{project_id}/{chapter_num}")
async def get_writing_chapter(project_id: str, chapter_num: int):
    try:
        chapter = get_writing_service().get_chapter(project_id, chapter_num)
        if chapter:
            return success_response(chapter)
        raise HTTPException(status_code=404, detail="章节未找到")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取章节失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/writing/chapter/{project_id}/{chapter_num}")
async def update_writing_chapter(project_id: str, chapter_num: int, chapter_data: Dict[str, Any]):
    try:
        chapter = get_writing_service().update_chapter(project_id, chapter_num, chapter_data)
        if not chapter:
            raise HTTPException(status_code=404, detail="小说不存在")
        return success_response({"chapter_num": chapter_num, "chapter": chapter})
    except Exception as e:
        logger.error(f"更新章节失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))
