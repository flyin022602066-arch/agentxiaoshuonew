from fastapi import APIRouter, HTTPException
from typing import Any, Dict
import logging

from app.services.chapter_service import get_chapter_service
from app.services.novel_service import get_novel_service
from app.api.responses import success_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["小说管理"])


@router.get("/novels")
async def list_novels():
    try:
        novels = get_novel_service().list_novels()
        return success_response({"novels": novels, "total": len(novels)})
    except Exception as e:
        logger.error(f"获取小说列表失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/novels")
async def create_novel(novel_data: Dict[str, Any]):
    try:
        result = get_novel_service().create_novel(novel_data)
        return success_response(result, "小说创建成功")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建小说失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/novels/{novel_id}")
async def get_novel(novel_id: str):
    try:
        novel = get_novel_service().get_novel(novel_id)
        if not novel:
            raise HTTPException(status_code=404, detail="小说不存在")
        return success_response(novel)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取小说详情失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/novels/{novel_id}")
async def update_novel(novel_id: str, novel_data: Dict[str, Any]):
    try:
        if not get_novel_service().update_novel(novel_id, novel_data):
            raise HTTPException(status_code=404, detail="小说不存在")
        return success_response(None, "小说已更新")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新小说失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/novels/{novel_id}")
async def delete_novel(novel_id: str):
    try:
        get_novel_service().delete_novel(novel_id)
        return success_response(None, "小说已删除")
    except Exception as e:
        logger.error(f"删除小说失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/novels/{novel_id}/chapters")
async def list_chapters(novel_id: str):
    try:
        chapters = get_chapter_service().list_chapters(novel_id)
        return success_response({"chapters": chapters, "total": len(chapters)})
    except Exception as e:
        logger.error(f"获取章节列表失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/novels/{novel_id}/chapters")
async def create_chapter(novel_id: str, chapter_data: Dict[str, Any]):
    try:
        from app.novel_db import get_novel_database

        db = get_novel_database()
        if not db.get_novel(novel_id):
            raise HTTPException(status_code=404, detail="小说不存在")

        chapter_num = chapter_data.get("chapter_num", 1)
        title = chapter_data.get("title", "")
        outline = chapter_data.get("outline", "")
        chapter_id = get_chapter_service().create_chapter(novel_id, chapter_num, title, outline)
        return success_response({"chapter_id": chapter_id, "chapter_num": chapter_num}, "章节创建成功")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建章节失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/novels/{novel_id}/chapters/{chapter_num}")
async def get_chapter(novel_id: str, chapter_num: int):
    try:
        chapter = get_chapter_service().get_chapter(novel_id, chapter_num)
        if not chapter:
            raise HTTPException(status_code=404, detail="章节不存在")
        return success_response(chapter)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取章节失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/novels/{novel_id}/chapters/{chapter_num}")
async def update_chapter(novel_id: str, chapter_num: int, chapter_data: Dict[str, Any]):
    try:
        from app.novel_db import get_novel_database

        db = get_novel_database()
        if not db.get_novel(novel_id):
            raise HTTPException(status_code=404, detail="小说不存在")
        chapter = get_chapter_service().save_chapter(
            novel_id=novel_id,
            chapter_num=chapter_num,
            content=chapter_data.get("content", ""),
            title=chapter_data.get("title", ""),
            outline=chapter_data.get("outline", ""),
            status=chapter_data.get("status", "draft"),
        )
        return success_response(chapter, "章节已更新")
    except Exception as e:
        logger.error(f"更新章节失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/novels/{novel_id}/chapters/{chapter_num}")
async def delete_chapter(novel_id: str, chapter_num: int):
    try:
        from app.novel_db import get_novel_database

        db = get_novel_database()
        if not db.get_novel(novel_id):
            raise HTTPException(status_code=404, detail="小说不存在")
        if not get_chapter_service().delete_chapter(novel_id, chapter_num):
            raise HTTPException(status_code=404, detail="章节不存在")
        return success_response({"chapter_num": chapter_num}, "章节已删除")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除章节失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/novels/{novel_id}/characters")
async def list_characters(novel_id: str):
    try:
        characters = get_novel_service().list_characters(novel_id)
        return success_response({"characters": characters, "total": len(characters)})
    except Exception as e:
        logger.error(f"获取人物列表失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/novels/{novel_id}/characters")
async def add_character(novel_id: str, character_data: Dict[str, Any]):
    try:
        result = get_novel_service().add_character(novel_id, character_data)
        return success_response(result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"添加人物失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/novels/{novel_id}/hooks")
async def list_hooks(novel_id: str):
    try:
        hooks = get_novel_service().list_hooks(novel_id)
        return success_response({"hooks": hooks, "total": len(hooks)})
    except Exception as e:
        logger.error(f"获取伏笔列表失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))
