# ==========================================
# 多 Agent 协作小说系统 - 小说架构师 Agent
# 负责全自动创作的核心 Agent
# ==========================================

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
import json
import httpx
import traceback

logger = logging.getLogger(__name__)


def _stringify_exception(error: Exception) -> str:
    message = str(error).strip()
    return message or error.__class__.__name__


class NovelArchitectAgent:
    """
    小说架构师 Agent
    负责全自动创作的核心规划和协调
    """
    
    def __init__(self, llm_client: Dict[str, Any]):
        self.llm_client = llm_client
        self.agent_id = "novel_architect"
        self.state = "idle"
        self.last_active = None

    def _resolve_request_timeout(self, max_tokens: int) -> httpx.Timeout:
        """全自动创作属于长任务，按产物复杂度放宽超时。"""
        base_timeout = int(self.llm_client.get('timeout', 60) or 60)
        # 3000 章宏观规划 / 大段 JSON 很容易超过常规 60s。
        read_timeout = max(base_timeout, 180 if max_tokens <= 2000 else 300)
        return httpx.Timeout(connect=30.0, read=float(read_timeout), write=30.0, pool=30.0)
    
    async def create_novel_blueprint(
        self,
        title: str,
        genre: str,
        description: str,
        chapter_count: int = 3000
    ) -> Dict[str, Any]:
        """
        创建小说蓝图（全自动）
        
        流程:
        1. 生成世界观地图
        2. 生成 3000 章宏观规划
        3. 生成人物体系
        4. 生成伏笔网络
        5. 整合所有设定
        """
        
        self.state = "working"
        self.last_active = datetime.now()
        
        try:
            # Step 1: 生成世界观地图
            logger.info(f"Step 1: 生成世界观地图 - {title}")
            world_map = await self._generate_world_map(title, genre, description, chapter_count)
            
            # Step 2: 生成宏观规划
            logger.info(f"Step 2: 生成 3000 章宏观规划")
            macro_plot = await self._generate_macro_plot(title, genre, world_map, chapter_count)
            
            # Step 3: 生成人物体系
            logger.info(f"Step 3: 生成人物体系")
            character_system = await self._generate_character_system(title, genre, description, world_map, macro_plot)
            
            # Step 4: 生成伏笔网络
            logger.info(f"Step 4: 生成伏笔网络")
            hook_network = await self._generate_hook_network(title, world_map, macro_plot)
            
            # Step 5: 整合蓝图
            blueprint = {
                "novel_info": {
                    "title": title,
                    "genre": genre,
                    "description": description,
                    "chapter_count": chapter_count,
                    "created_at": datetime.now().isoformat()
                },
                "world_map": world_map,
                "macro_plot": macro_plot,
                "character_system": character_system,
                "hook_network": hook_network,
                "status": "completed",
                "completion_time": datetime.now().isoformat()
            }
            
            self.state = "idle"
            return blueprint
            
        except Exception as e:
            logger.error(f"创建蓝图失败：{e}")
            logger.error(traceback.format_exc())
            self.state = "error"
            return {
                "status": "error",
                "error": _stringify_exception(e)
            }
    
    async def _generate_world_map(self, title: str, genre: str, description: str, chapter_count: int) -> Dict[str, Any]:
        """生成世界观地图 - 使用简介中的关键设定"""
        
        # 强化简介信息的引导
        description_hint = ""
        if description:
            description_hint = f"""
【用户简介】{description}

请确保世界观设定与简介中的关键信息保持一致：
- 如果简介中提到了特定地点、势力或设定，请纳入世界观
- 如果简介暗示了某种修炼体系或力量体系，请据此设计
- 世界背景应该为简介中的故事提供合理的舞台
"""
        
        prompt = f"""你是一位专业的世界观架构师。为小说《{title}》生成世界观设定。

类型：{genre}
{description_hint}
请用 JSON 格式输出：
{{
  "world_name": "世界名称",
  "power_system": {{
    "name": "修炼体系",
    "levels": ["等级 1", "等级 2", "等级 3"]
  }},
  "main_factions": [
    {{"name": "势力 1", "description": "描述"}}
  ],
  "background": "世界背景（500 字内，需与简介中的故事背景相容）"
}}

只需 JSON，不要其他说明。"""
        
        response = await self._call_llm(prompt, max_tokens=1600)
        
        try:
            world_map = self._extract_json(response)
            if not isinstance(world_map, dict) or world_map.get("raw"):
                raise ValueError(f"世界观 JSON 解析失败，模型返回内容片段：{response[:300]}")
            return world_map
        except Exception as e:
            logger.error(f"解析世界观失败：{e}")
            raise ValueError(f"世界观生成失败：{e}") from e
    
    async def _generate_macro_plot(self, title: str, genre: str, world_map: Dict, chapter_count: int) -> Dict[str, Any]:
        """生成宏观规划 - 基于世界观和故事走向"""
        target_volumes = min(12, max(6, chapter_count // 300))
        
        # 从世界观中提取关键背景
        world_background = world_map.get('background', '')[:300] if world_map else ''
        power_system = world_map.get('power_system', {}).get('name', '修炼体系') if world_map else '修炼体系'
        
        prompt = f"""你是一位专业的长篇规划师。请为小说《{title}》制定宏观规划，总计划章节数为 {chapter_count} 章。

类型：{genre}
世界观核心：{world_background}
力量体系：{power_system}

不要尝试列出每一章，而是按"卷"来进行宏观规划。
为了保证 JSON 稳定，请只输出 {target_volumes} 卷左右的摘要信息，每卷字段必须简短，冲突和目标各不超过 30 个字。
请严格输出合法 JSON，不能有注释、不能省略逗号、不能输出 JSON 之外的任何说明。
请用 JSON 格式输出：
{{
  "total_chapters": {chapter_count},
  "volume_count": {target_volumes},
  "volumes": [
    {{
      "volume_num": 1,
      "volume_title": "第一卷标题",
      "chapters": "1-300",
      "main_goal": "本卷目标",
      "conflict": "核心冲突",
      "climax_chapter": 300
    }}
  ],
  "rhythm_control": {{
    "small_climax": "每 10 章一个小高潮",
    "medium_climax": "每 20 章一个中高峰",
    "big_climax": "每 100 章一个大高潮"
  }}
}}

只要 JSON，不要解释。"""
        
        response = await self._call_llm(prompt, max_tokens=1600)
        
        try:
            macro_plot = self._extract_json(response)
            if not isinstance(macro_plot, dict) or macro_plot.get("raw"):
                raise ValueError(f"宏观规划 JSON 解析失败，模型返回内容片段：{response[:300]}")
            return macro_plot
        except Exception as e:
            logger.error(f"解析规划失败：{e}")
            raise ValueError(f"宏观规划生成失败：{e}") from e
    
    async def _generate_character_system(self, title: str, genre: str, description: str, world_map: Dict, macro_plot: Dict) -> Dict[str, Any]:
        """生成人物体系 - 使用用户提供的简介信息"""
        
        # 从简介中提取主角名字等关键信息
        protagonist_hint = ""
        if description:
            # 简介中可能包含主角名字，让 LLM 优先使用
            protagonist_hint = f"""
【重要】用户提供的简介：{description}

请仔细阅读简介，如果简介中提到了主角名字、背景或特征，必须优先使用简介中的设定！
如果简介中提到了其他关键角色，也请一并纳入人物体系。
"""
        
        prompt = f"""为小说《{title}》生成主角设定。

类型：{genre}
{protagonist_hint}
请用 JSON 格式输出：
{{
  "protagonist": {{
    "name": "主角名（如果简介中已指定，必须使用简介中的名字）",
    "age": 18,
    "background": "背景故事（200 字，如果简介中已有背景，请扩展而非推翻）",
    "personality": ["性格 1", "性格 2"],
    "goal": "核心目标"
  }},
  "key_characters": [
    {{
      "name": "重要配角名",
      "role": "角色定位",
      "description": "简要描述"
    }}
  ]
}}

只需 JSON，不要其他说明。"""
        
        response = await self._call_llm(prompt, max_tokens=1200)
        
        try:
            characters = self._extract_json(response)
            if not isinstance(characters, dict) or characters.get("raw"):
                raise ValueError(f"人物设定 JSON 解析失败，模型返回内容片段：{response[:300]}")
            return characters
        except Exception as e:
            logger.error(f"解析人物失败：{e}")
            raise ValueError(f"人物体系生成失败：{e}") from e
    
    async def _generate_hook_network(self, title: str, world_map: Dict, macro_plot: Dict) -> Dict[str, Any]:
        """生成伏笔网络 - 简化版"""
        return {
            "short_term": [{"description": "第一个小谜团", "reveal_chapter": 5}],
            "medium_term": [{"description": "中期大谜团", "reveal_chapter": 10}],
            "long_term": [{"description": "终极谜团", "reveal_chapter": 20}],
            "ultimate": [{"description": "全书核心谜团"}]
        }
    
    def _extract_json(self, text: str) -> Dict[str, Any]:
        """从文本中提取 JSON - 增强版"""
        import re
        
        # 尝试先匹配 ```json ... ``` 格式
        code_block_match = re.search(r'```json\s*([\s\S]*?)\s*```', text, re.IGNORECASE)
        if code_block_match:
            text = code_block_match.group(1)
        
        # 查找 JSON 起始和结束位置
        json_start = text.find('{')
        json_end = text.rfind('}') + 1
        
        if json_start < 0 or json_end <= json_start:
            raise ValueError("未找到 JSON 内容")

        json_str = text[json_start:json_end]
        try:
            return json.loads(json_str)
        except Exception as e:
            logger.error(f"提取 JSON 失败：{e}")
            raise ValueError(f"JSON 解析失败：{e}；内容片段：{json_str[:300]}") from e
    
    async def _call_llm(self, prompt: str, max_tokens: int = 4000) -> str:
        """调用 LLM API"""
        if not self.llm_client:
            raise Exception("LLM 未配置")
        
        api_key = self.llm_client['api_key']
        base_url = self.llm_client['base_url'].rstrip('/')
        model = self.llm_client['model']
        timeout = self._resolve_request_timeout(max_tokens)
        endpoint = self.llm_client.get('endpoint', '/v1/chat/completions')
        if not str(endpoint).startswith('/'):
            endpoint = f'/{endpoint}'
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': model,
            'messages': [
                {'role': 'system', 'content': '你是一位专业的小说架构师，擅长构建宏大而自洽的世界观和长篇规划。'},
                {'role': 'user', 'content': prompt}
            ],
            'max_tokens': max_tokens,
            'temperature': 0.7
        }
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{base_url}{endpoint}",
                headers=headers,
                json=payload
            )
            
            if response.status_code == 200:
                data = response.json()
                return data['choices'][0]['message']['content']
            else:
                raise Exception(f"LLM API 调用失败：{response.status_code} - {response.text}")


# ========== 全自动创作系统 ==========

class AutoCreationSystem:
    """
    全自动创作系统
    一键生成完整小说设定和章节
    """
    
    def __init__(self, llm_client: Dict[str, Any]):
        self.llm_client = llm_client
        self.architect = NovelArchitectAgent(llm_client)
        self.blueprint: Optional[Dict[str, Any]] = None

    def _resolve_author_style(self, requested_style: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        from app.author_styles import get_author_style

        requested_style = requested_style or {}
        style_id = requested_style.get('style_id') or 'default'
        return get_author_style(style_id)
    
    async def create_novel_from_scratch(
        self,
        title: str,
        genre: str,
        description: str,
        chapter_count: int = 3000,
        auto_style: Optional[Dict[str, Any]] = None,
        progress_callback=None,
    ) -> Dict[str, Any]:
        """
        从零开始创建小说（全自动）
        
        用户只需要提供:
        - 书名
        - 类型
        - 一句话简介
        
        系统自动生成:
        - 世界观地图
        - 3000 章规划
        - 人物体系
        - 伏笔网络
        - 第一章正文
        """
        
        logger.info(f"开始全自动创作：{title}")
        resolved_style = self._resolve_author_style(auto_style)

        def _progress(progress: int, stage: str):
            if progress_callback:
                try:
                    progress_callback(progress, stage)
                except Exception:
                    pass
        
        # Step 1: 创建蓝图
        _progress(15, "正在生成世界观地图")
        self.blueprint = await self.architect.create_novel_blueprint(
            title, genre, description, chapter_count
        )
        
        if self.blueprint.get('status') == 'error':
            if not self.blueprint.get('error'):
                self.blueprint['error'] = '蓝图生成失败，未返回具体错误信息'
            logger.error(f"全自动创作蓝图失败：{self.blueprint.get('error')}")
            return self.blueprint
        
        # Step 2: 保存蓝图到数据库
        _progress(70, "正在保存蓝图到小说设置")
        from app.novel_db import get_novel_database
        db = get_novel_database()
        
        # 创建小说
        blueprint_payload = {
            "world_map": self.blueprint.get("world_map", {}),
            "macro_plot": self.blueprint.get("macro_plot", {}),
            "character_system": self.blueprint.get("character_system", {}),
            "hook_network": self.blueprint.get("hook_network", {}),
        }
        novel_id = db.create_novel(
            title,
            genre,
            description,
            settings={
                "blueprint": blueprint_payload,
                **blueprint_payload,
                "auto_style": auto_style,
                "active_style": resolved_style,
            },
        )
        
        # 持久化关键蓝图产物，供后续续写直接复用
        protagonist = (self.blueprint.get("character_system") or {}).get("protagonist") or {}
        if protagonist.get("name"):
            try:
                db.add_character(
                    novel_id,
                    name=protagonist.get("name", "主角"),
                    role="protagonist",
                    description=protagonist.get("background", ""),
                    traits=protagonist.get("personality", []),
                )
            except Exception as e:
                logger.warning(f"持久化主角信息失败：{e}")

        hook_network = self.blueprint.get("hook_network") or {}
        for hook_type, hook_items in hook_network.items():
            if not isinstance(hook_items, list):
                continue
            for item in hook_items:
                description = item.get("description") if isinstance(item, dict) else None
                if not description:
                    continue
                try:
                    db.add_plot_hook(
                        novel_id,
                        description=description,
                        hook_type=hook_type,
                        chapter_introduced=item.get("reveal_chapter", 0) if isinstance(item, dict) else 0,
                    )
                except Exception as e:
                    logger.warning(f"持久化伏笔失败：{e}")
        
        # Step 3: 生成第一章
        _progress(85, "正在创作第一章")
        first_chapter = await self._generate_first_chapter(
            novel_id,
            self.blueprint,
            resolved_style,
            progress_callback=_progress,
        )
        if first_chapter.get("status") == "error":
            error_message = first_chapter.get("message") or first_chapter.get("error") or "第一章生成失败"
            logger.error(f"全自动创作第一章失败：{error_message}")
            return {
                "status": "error",
                "error": error_message,
                "novel_id": novel_id,
                "blueprint": self.blueprint,
                "first_chapter": first_chapter,
            }
        
        return {
            "status": "success",
            "novel_id": novel_id,
            "blueprint": self.blueprint,
            "auto_style": resolved_style,
            "first_chapter": first_chapter
        }
    
    async def _generate_first_chapter(
        self,
        novel_id: str,
        blueprint: Dict,
        auto_style: Optional[Dict[str, Any]] = None,
        progress_callback=None,
    ) -> Dict[str, Any]:
        """生成第一章 - 修复版：严格验证内容有效性"""
        from app.workflow_executor import get_workflow_executor
        from app.novel_db import get_novel_database
        import json
        
        executor = get_workflow_executor()
        db = get_novel_database()
        
        # 从蓝图中提取第一章大纲
        chapter_outline = self._extract_first_chapter_outline(blueprint)
        
        logger.info(f"开始生成第一章，大纲：{chapter_outline[:100]}...")
        
        # 先创建章节记录
        try:
            db.create_chapter(novel_id, 1, "第一章 开始", chapter_outline)
            logger.info(f"[OK] 已创建章节记录：{novel_id} 第 1 章")
        except Exception as e:
            logger.error(f"[FAIL] 创建章节记录失败：{e}，继续生成内容")
        
        # 生成第一章内容
        logger.info(f"调用 workflow_executor 生成第一章内容...")
        def _chapter_progress(executor_progress: int, stage: str):
            if not progress_callback:
                return
            mapped_progress = min(99, 85 + int(executor_progress * 0.14))
            progress_callback(mapped_progress, f"第一章创作中：{stage}")

        result = await executor.execute_chapter_workflow(
            novel_id=novel_id,
            chapter_num=1,
            outline=chapter_outline,
            word_count_target=2200,
            style=(auto_style or {}).get('style_id') or (auto_style or {}).get('mode') or 'default',
            progress_callback=_chapter_progress,
        )
        
        logger.info(f"workflow_executor 返回：status={result.get('status')}, word_count={result.get('word_count', 0)}")
        
        # 修复：严格检查内容是否有效
        content = result.get('content', '')
        if result.get('status') == 'success' and content and len(content) > 100:
            logger.info(f"[OK] 第一章生成成功，字数：{len(content)}")
            try:
                outline_summary = result.get('outline_summary') if isinstance(result, dict) else None
                db.update_chapter(
                    novel_id, 1,
                    content=content,
                    title="第一章",
                    outline=chapter_outline,
                    outline_summary=outline_summary,
                    status='published'
                )
                logger.info(f"[OK] 已保存第一章内容到数据库：{novel_id}")
            except Exception as e:
                logger.error(f"[FAIL] 保存章节内容失败：{e}")
                import traceback
                logger.error(traceback.format_exc())
        else:
            # 内容无效，记录详细错误
            logger.error(f"[FAIL] 第一章生成失败或内容为空")
            logger.error(f"   status: {result.get('status')}")
            logger.error(f"   content length: {len(content) if content else 0}")
            logger.error(f"   message: {result.get('message', 'N/A')}")
            logger.error(f"   full result: {json.dumps(result, ensure_ascii=False)[:500]}")
        
        return result
    
    def _extract_first_chapter_outline(self, blueprint: Dict) -> str:
        """从蓝图中提取第一章大纲 - 使用简介和设定"""
        novel_info = blueprint.get('novel_info', {})
        character_system = blueprint.get('character_system', {})
        world_map = blueprint.get('world_map', {})
        
        protagonist = character_system.get('protagonist', {})
        protagonist_name = protagonist.get('name', '主角')
        protagonist_goal = protagonist.get('goal', '')
        protagonist_background = protagonist.get('background', '')[:100] if protagonist.get('background') else ''
        
        world_name = world_map.get('world_name', '')
        power_system = world_map.get('power_system', {}).get('name', '')
        
        # 构建第一章大纲
        outline_parts = [
            f"主角{protagonist_name}登场",
        ]
        
        if protagonist_background:
            outline_parts.append(f"背景：{protagonist_background}")
        
        if world_name:
            outline_parts.append(f"世界观引入：{world_name}")
        
        if power_system:
            outline_parts.append(f"力量体系：{power_system}")
        
        if protagonist_goal:
            outline_parts.append(f"核心目标暗示：{protagonist_goal}")
        
        outline_parts.append("引入第一个小冲突")
        
        return "；".join(outline_parts)


# ========== 全局单例 ==========

_creation_system: Optional[AutoCreationSystem] = None


def get_auto_creation_system() -> AutoCreationSystem:
    """获取全自动创作系统单例"""
    global _creation_system
    from app.config_db import get_config_database
    db = get_config_database()

    default_provider = db.get_default_provider()
    provider_config = db.get_provider(default_provider)

    if not (provider_config and provider_config.get('api_key')):
        raise Exception("LLM 未配置")

    llm_client = {
        'api_key': provider_config['api_key'],
        'base_url': provider_config['base_url'],
        'model': provider_config['model'],
        'timeout': provider_config.get('timeout', 60),
        'endpoint': provider_config.get('endpoint', '/v1/chat/completions')
    }

    # 运行时配置支持热更新：配置变化后重建系统，避免继续使用旧 provider。
    if _creation_system is None or _creation_system.llm_client != llm_client:
        _creation_system = AutoCreationSystem(llm_client)

    return _creation_system
