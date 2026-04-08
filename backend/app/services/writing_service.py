from typing import Any, Dict
import logging

from app.novel_db import get_novel_database
from app.services.chapter_service import get_chapter_service
from app.services.chapter_generator import ChapterGenerator
from app.tasks.task_manager import get_task_manager, TaskStatus
from app.workflow_executor import get_workflow_executor
from app.services.style_learner import StyleLearner

logger = logging.getLogger(__name__)

PLATFORM_STYLE_IDS = {"fanqiao", "qimao"}


def _build_character_notes(character_system: Dict[str, Any], db_characters: list[Dict[str, Any]]) -> str:
    notes = []
    protagonist = (character_system or {}).get("protagonist") or {}
    if protagonist:
        notes.append(
            f"主角：{protagonist.get('name', '未命名')}；目标：{protagonist.get('goal', '')}；背景：{protagonist.get('background', '')}；性格：{'、'.join(protagonist.get('personality', []))}"
        )

    for character in db_characters:
        notes.append(
            f"角色：{character.get('name', '')}；定位：{character.get('role', '')}；描述：{character.get('description', '')}"
        )

    return "\n".join(filter(None, notes))


def _augment_outline_with_story_context(outline: str, macro_plot: Dict[str, Any], hook_network: Dict[str, Any]) -> str:
    context_blocks = []

    volumes = (macro_plot or {}).get("volumes") or []
    if volumes:
        current_volume = volumes[0]
        context_blocks.append(
            f"【宏观规划参考】当前主线：{current_volume.get('main_goal', '')}；核心冲突：{current_volume.get('conflict', '')}"
        )

    hook_lines = []
    for hook_type, items in (hook_network or {}).items():
        if not isinstance(items, list):
            continue
        for item in items[:3]:
            if isinstance(item, dict) and item.get("description"):
                hook_lines.append(f"{hook_type}: {item['description']}")
    if hook_lines:
        context_blocks.append("【伏笔参考】" + "；".join(hook_lines))

    if not context_blocks:
        return outline

    return f"{outline}\n\n" + "\n".join(context_blocks)


def _append_character_context(outline: str, character_notes: str) -> str:
    if not character_notes:
        return outline
    return f"{outline}\n\n【人物体系参考】\n{character_notes}"


class WritingService:
    style_learner: StyleLearner

    def __init__(self):
        self.db = get_novel_database()
        self.chapter_service = get_chapter_service()
        self.style_learner = StyleLearner()

    async def create_chapter_workflow(self, chapter_data: Dict[str, Any], task_id: str | None = None) -> Dict[str, Any]:
        chapter_num = chapter_data.get("chapter_num", 1)
        novel_id = chapter_data.get("novel_id", "default")
        outline = chapter_data.get("outline", "")
        word_count_target = chapter_data.get("word_count_target", 3000)
        style = chapter_data.get("style", "default")
        platform = chapter_data.get("platform")
        style_context = chapter_data.get("style_context") or {}
        creative_settings = chapter_data.get("creative_settings") or {}

        logger.info(f"收到章节请求：novel_id={novel_id}, chapter_num={chapter_num}, word_count_target={word_count_target}, style={style}")
        if not outline:
            raise ValueError("大纲不能为空")

        novel = self.db.get_novel(novel_id) or {}
        settings = novel.get("settings") or {}
        blueprint = settings.get("blueprint") or {}
        macro_plot = settings.get("macro_plot") or blueprint.get("macro_plot") or {}
        world_map = settings.get("world_map") or blueprint.get("world_map") or {}
        character_system = settings.get("character_system") or blueprint.get("character_system") or {}
        hook_network = settings.get("hook_network") or blueprint.get("hook_network") or {}
        protagonist_halo = character_system.get("protagonist") or {}
        character_notes = _build_character_notes(character_system, self.db.get_characters(novel_id))
        enriched_outline = _augment_outline_with_story_context(outline, macro_plot, hook_network)
        enriched_outline = _append_character_context(enriched_outline, character_notes)

        resolved_platform = None
        platform_resolution = "none"
        style_context_platform = style_context.get("style_id") if style_context else None
        if platform in PLATFORM_STYLE_IDS:
            resolved_platform = platform
            platform_resolution = "user_selected"
        elif style_context_platform in PLATFORM_STYLE_IDS:
            resolved_platform = style_context_platform
            platform_resolution = "style_context"
        else:
            recommendation_source = f"{outline}\n\n{character_notes}".strip()
            recommended = self.style_learner.match_platform(recommendation_source)
            if recommended in PLATFORM_STYLE_IDS:
                resolved_platform = recommended
                platform_resolution = "auto_recommended"

        if resolved_platform:
            style = resolved_platform

        # 进度回调 + Agent 状态更新
        def _progress(pct, stage):
            if task_id:
                try:
                    task_manager = get_task_manager()
                    task_manager.update_task(task_id, progress=pct, current_stage=stage)
                except Exception as e:
                    logger.warning(f"更新任务进度失败：{e}")
            
            # 更新 Agent 状态
            try:
                from app.agents.registry import set_agent_state
                if pct < 30:
                    set_agent_state('plot_agent', 'working')
                    set_agent_state('writer_agent', 'idle')
                    set_agent_state('editor_agent', 'idle')
                elif pct < 70:
                    set_agent_state('plot_agent', 'idle')
                    set_agent_state('writer_agent', 'working')
                    set_agent_state('editor_agent', 'idle')
                elif pct < 95:
                    set_agent_state('writer_agent', 'idle')
                    set_agent_state('editor_agent', 'working')
                else:
                    set_agent_state('editor_agent', 'idle')
            except Exception as e:
                logger.warning(f"更新 Agent 状态失败：{e}")

        executor = get_workflow_executor()
        
        if not executor.llm_client:
            return {
                'status': 'error',
                'message': 'LLM 未配置，请先在配置页面设置 API Key'
            }

        _progress(10, "正在生成章节...")

        _progress(30, "AI 正在创作中...")

        # 将风格强度一并传递给工作流，确保分段生成阶段能按风格强度调整输出
        result = await executor.execute_chapter_workflow(
            novel_id=novel_id,
            chapter_num=chapter_num,
            outline=enriched_outline,
            word_count_target=word_count_target,
            style=(style_context.get("style_id") or style),
            style_strength=(creative_settings.get("strength") if creative_settings else None),
            macro_plot=macro_plot or None,
            world_map=world_map or None,
            protagonist_halo=protagonist_halo or None,
            progress_callback=_progress,
            min_style_score=40,
        )

        if creative_settings:
            try:
                merged_settings = {
                    **settings,
                    "creative_settings": creative_settings,
                }
                self.db.update_novel(novel_id, settings=merged_settings)
            except Exception as e:
                logger.warning(f"保存创作设置失败：{e}")

        content = result.get('content', '')
        persisted_outline = result.get('outline_summary') or outline
        
        _progress(80, "保存章节...")
        
        if content and len(content) > 100:
            # 保存到数据库
            try:
                self.chapter_service.save_chapter(
                    novel_id=novel_id,
                    chapter_num=chapter_num,
                    content=content,
                    title=f"第{chapter_num}章",
                    outline=persisted_outline,
                    status="draft"
                )
                logger.info(f"章节已保存：{novel_id} 第{chapter_num}章，{len(content)}字")
            except Exception as e:
                logger.error(f"保存章节失败：{e}")
            
            _progress(100, "创作完成")
            
            # 重置所有 Agent 状态
            try:
                from app.agents.registry import set_agent_state
                set_agent_state('plot_agent', 'idle')
                set_agent_state('writer_agent', 'idle')
                set_agent_state('editor_agent', 'idle')
            except Exception as e:
                pass
            
            return {
                'status': result.get('status', 'success'),
                'content': content,
                'word_count': result.get('word_count', len(content)),
                'chapter_num': chapter_num,
                'workflow_id': result.get('workflow_id', f"wf_{novel_id}_{chapter_num}"),
                'platform': resolved_platform or style,
                'platform_resolution': platform_resolution,
            }
        else:
            # 重置 Agent 状态
            try:
                from app.agents.registry import set_agent_state
                set_agent_state('plot_agent', 'idle')
                set_agent_state('writer_agent', 'idle')
                set_agent_state('editor_agent', 'idle')
            except Exception as e:
                pass
            
            return {
                'status': 'error',
                'message': result.get('message') or f'生成内容过短（{len(content) if content else 0}字），请重试',
                'chapter_num': chapter_num
            }

    async def export_chapter_variants(self, novel_id: str, chapter_num: int, target: str = "both") -> Dict[str, Any]:
        chapter = self.chapter_service.get_chapter(novel_id, chapter_num)
        if not chapter:
            raise ValueError("章节不存在")

        content = chapter.get("content", "")
        title = chapter.get("title", f"第{chapter_num}章")

        async def _build_variant(platform: str) -> Dict[str, Any]:
            if platform == "fanqiao":
                return {
                    "platform": "fanqiao",
                    "title": title,
                    "content": await self._export_fanqiao_variant(content),
                }
            if platform == "qimao":
                return {
                    "platform": "qimao",
                    "title": title,
                    "content": await self._export_qimao_variant(content),
                }
            raise ValueError(f"不支持的导出目标：{platform}")

        if target == "both":
            variants = [await _build_variant("fanqiao"), await _build_variant("qimao")]
        else:
            variants = [await _build_variant(target)]

        return {
            "novel_id": novel_id,
            "chapter_num": chapter_num,
            "target": target,
            "variants": variants,
        }

    async def _export_fanqiao_variant(self, content: str) -> str:
        return content

    async def _export_qimao_variant(self, content: str) -> str:
        return content

    def get_chapter(self, project_id: str, chapter_num: int):
        return self.chapter_service.get_chapter(project_id, chapter_num)

    def update_chapter(self, project_id: str, chapter_num: int, chapter_data: Dict[str, Any]):
        if not self.db.get_novel(project_id):
            return None
        return self.chapter_service.save_chapter(
            novel_id=project_id,
            chapter_num=chapter_num,
            content=chapter_data.get("content", ""),
            title=chapter_data.get("title", ""),
            outline=chapter_data.get("outline", ""),
            status=chapter_data.get("status", "draft"),
        )


_writing_service: WritingService | None = None


def get_writing_service() -> WritingService:
    global _writing_service
    if _writing_service is None:
        _writing_service = WritingService()
    return _writing_service
