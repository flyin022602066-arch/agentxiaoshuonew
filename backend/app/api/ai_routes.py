from fastapi import APIRouter, HTTPException
from typing import Any, Dict
import logging

from app.api.responses import success_response
from app.services.ai_service import get_ai_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["AI 创作"])


@router.get("/ai/templates")
async def list_templates():
    try:
        templates = get_ai_service().list_templates()
        return success_response(templates, f"获取到 {sum(len(v) for v in templates.values())} 个专业模板")
    except Exception as e:
        logger.error(f"获取模板失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ai/generate-outline")
async def ai_generate_outline(data: Dict[str, Any]):
    try:
        result = await get_ai_service().generate_outline(data)
        return success_response(result, f"使用【{result.get('template_used', '专业模板')}】生成大纲成功")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"生成大纲失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ai/generate-characters")
async def ai_generate_characters(data: Dict[str, Any]):
    try:
        result = await get_ai_service().generate_characters(data)
        return success_response(result, f"生成了 {len(result.get('characters', []))} 个人物")
    except Exception as e:
        logger.error(f"生成人物失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ai/generate-chapter-outline")
async def ai_generate_chapter_outline(data: Dict[str, Any]):
    try:
        result = await get_ai_service().generate_chapter_outline(data)
        return success_response(result, "章节大纲生成成功")
    except Exception as e:
        logger.error(f"生成章节大纲失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ai/generate-style-preview")
async def ai_generate_style_preview(data: Dict[str, Any]):
    try:
        result = await get_ai_service().generate_style_preview(data)
        return success_response(result, "风格试写生成成功")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"生成风格试写失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ai/generate-plot")
async def ai_generate_plot(data: Dict[str, Any]):
    try:
        result = await get_ai_service().generate_plot(data)
        return success_response(result, "情节设计生成成功")
    except Exception as e:
        logger.error(f"生成情节失败：{e}")
        raise HTTPException(status_code=500, detail=str(e))
