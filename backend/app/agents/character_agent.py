# ==========================================
# 多 Agent 协作小说系统 - 人物设计师 Agent
# ==========================================

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class CharacterAgent(BaseAgent):
    """
    人物设计师 Agent
    
    职责:
    1. 设计人物设定（外貌、性格、背景）
    2. 构建人物关系网
    3. 设计人物成长弧线
    4. 确保人物行为一致性（不 OOC）
    5. 个性化对话风格
    """
    
    def get_system_prompt(self) -> str:
        return """你是一位专业的人物设计师，擅长塑造立体、真实的角色。

你的专长:
1. **人物设定**: 外貌、性格、背景、动机
2. **关系网络**: 人物之间的关系构建
3. **成长弧线**: 人物如何随故事成长变化
4. **对话个性化**: 每个人物独特的说话方式
5. **行为一致性**: 确保人物行为符合设定

请记住：好的人物是立体的、有矛盾的、会成长的。"""
    
    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """执行人物任务"""
        action = task.get('action')
        
        if action == 'create_character':
            return await self.create_character(task)
        elif action == 'update_character_state':
            return await self.update_character_state(task)
        elif action == 'design_relationships':
            return await self.design_relationships(task)
        elif action == 'check_character_consistency':
            return await self.check_character_consistency(task)
        elif action == 'design_character_arc':
            return await self.design_character_arc(task)
        elif action == 'prepare_character_states':
            return await self.prepare_character_states(task)
        else:
            raise ValueError(f"未知动作：{action}")
    
    async def create_character(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        创建人物设定
        
        输入:
        {
            "name": "张三",
            "role": "protagonist/antagonist/supporting/minor",
            "story_context": "故事背景",
            "requirements": {...}
        }
        
        输出:
        {
            "status": "success",
            "character": {
                "character_id": "char_001",
                "name": "张三",
                "role": "protagonist",
                "appearance": {...},
                "personality": {...},
                "background": {...},
                "goals": {...},
                "relationships": [...],
                "dialogue_style": {...}
            }
        }
        """
        name = task.get('name', '')
        role = task.get('role', 'supporting')
        story_context = task.get('story_context', '')
        requirements = task.get('requirements', {})
        
        logger.info(f"创建人物：{name} ({role})")
        self.state = "working"
        self.last_active = datetime.now()
        
        try:
            prompt = self._build_create_character_prompt(
                name, role, story_context, requirements
            )
            
            result = await self.call_llm(prompt, temperature=0.5)
            character = self._parse_json(result)
            
            # 生成人物 ID
            character_id = f"char_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{name[:3]}"
            character['character_id'] = character_id
            
            # 存储到记忆
            if self.memory_engine:
                await self.memory_engine.store({
                    "type": "character",
                    "character_id": character_id,
                    "character": character,
                    "timestamp": datetime.now().isoformat()
                })
            
            return {
                "status": "success",
                "character": character,
                "character_id": character_id
            }
        
        except Exception as e:
            logger.error(f"人物创建失败：{e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "message": "人物创建失败"
            }
        
        finally:
            self.state = "idle"
    
    async def update_character_state(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        更新人物状态
        
        输入:
        {
            "character_id": "char_001",
            "chapter_num": 5,
            "new_state": {
                "location": "京城",
                "emotional_state": "tense",
                "current_goal": "寻找真相",
                "relationships_changed": [...]
            }
        }
        
        输出:
        {
            "status": "success",
            "character_id": "char_001",
            "updated_state": {...},
            "state_history": [...]
        }
        """
        character_id = task.get('character_id')
        chapter_num = task.get('chapter_num')
        new_state = task.get('new_state', {})
        
        logger.info(f"更新人物状态：{character_id} (第{chapter_num}章)")
        self.state = "working"
        self.last_active = datetime.now()
        
        try:
            # 获取当前人物设定
            if self.memory_engine:
                current_char = await self.memory_engine.retrieve({
                    "type": "character",
                    "character_id": character_id
                })
            else:
                current_char = {}
            
            # 更新状态
            updated_state = {
                "character_id": character_id,
                "chapter_num": chapter_num,
                "timestamp": datetime.now().isoformat(),
                **new_state
            }
            
            # 记录状态历史
            state_history = current_char.get('state_history', [])
            state_history.append(updated_state)
            
            return {
                "status": "success",
                "character_id": character_id,
                "updated_state": updated_state,
                "state_history": state_history[-5:]  # 最近 5 个状态
            }
        
        except Exception as e:
            logger.error(f"人物状态更新失败：{e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "message": "人物状态更新失败"
            }
        
        finally:
            self.state = "idle"
    
    async def design_relationships(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        设计人物关系
        
        输入:
        {
            "characters": ["char_001", "char_002", ...],
            "story_context": "故事背景",
            "relationship_types": ["friend", "enemy", "lover", ...]
        }
        
        输出:
        {
            "status": "success",
            "relationships": [
                {
                    "relationship_id": "rel_001",
                    "character_1": "char_001",
                    "character_2": "char_002",
                    "type": "friend",
                    "description": "关系描述",
                    "strength": 8,
                    "history": "关系历史",
                    "conflicts": ["潜在冲突"]
                }
            ]
        }
        """
        characters = task.get('characters', [])
        story_context = task.get('story_context', '')
        relationship_types = task.get('relationship_types', [])
        
        logger.info(f"设计人物关系：{len(characters)}个人物")
        self.state = "working"
        self.last_active = datetime.now()
        
        try:
            prompt = self._build_relationship_design_prompt(
                characters, story_context, relationship_types
            )
            
            result = await self.call_llm(prompt, temperature=0.5)
            relationships = self._parse_json_list(result)
            
            # 生成关系 ID
            for rel in relationships:
                rel['relationship_id'] = f"rel_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{len(relationships)}"
            
            return {
                "status": "success",
                "relationships": relationships,
                "relationship_count": len(relationships)
            }
        
        except Exception as e:
            logger.error(f"人物关系设计失败：{e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "message": "人物关系设计失败"
            }
        
        finally:
            self.state = "idle"
    
    async def check_character_consistency(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        检查人物一致性
        
        输入:
        {
            "character_id": "char_001",
            "chapter_content": "章节内容",
            "character_actions": ["行动 1", "行动 2"]
        }
        
        输出:
        {
            "status": "success",
            "consistent": true/false,
            "issues": [
                {
                    "type": "personality/behavior/dialogue/goal",
                    "description": "问题描述",
                    "severity": "low/medium/high"
                }
            ]
        }
        """
        character_id = task.get('character_id')
        chapter_content = task.get('chapter_content', '')
        character_actions = task.get('character_actions', [])
        
        logger.info(f"检查人物一致性：{character_id}")
        self.state = "working"
        self.last_active = datetime.now()
        
        try:
            # 获取人物设定
            if self.memory_engine:
                character = await self.memory_engine.retrieve({
                    "type": "character",
                    "character_id": character_id
                })
            else:
                character = {}
            
            prompt = self._build_consistency_check_prompt(
                character, chapter_content, character_actions
            )
            
            result = await self.call_llm(prompt, temperature=0.3)
            check_result = self._parse_json(result)
            
            return {
                "status": "success",
                "consistent": check_result.get('consistent', True),
                "issues": check_result.get('issues', []),
                "suggestions": check_result.get('suggestions', [])
            }
        
        except Exception as e:
            logger.error(f"人物一致性检查失败：{e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "message": "人物一致性检查失败"
            }
        
        finally:
            self.state = "idle"
    
    async def design_character_arc(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        设计人物成长弧线
        
        输入:
        {
            "character_id": "char_001",
            "story_span": "1-100 章",
            "theme": "成长与救赎"
        }
        
        输出:
        {
            "status": "success",
            "character_arc": {
                "starting_state": "起始状态",
                "ending_state": "最终状态",
                "key_milestones": [
                    {"chapter": 10, "event": "转折事件 1"},
                    {"chapter": 30, "event": "转折事件 2"}
                ],
                "internal_change": "内心变化",
                "external_change": "外在变化"
            }
        }
        """
        character_id = task.get('character_id')
        story_span = task.get('story_span', '')
        theme = task.get('theme', '')
        
        logger.info(f"设计人物弧线：{character_id}")
        self.state = "working"
        self.last_active = datetime.now()
        
        try:
            prompt = self._build_character_arc_prompt(
                character_id, story_span, theme
            )
            
            result = await self.call_llm(prompt, temperature=0.5)
            arc = self._parse_json(result)
            
            return {
                "status": "success",
                "character_arc": arc,
                "milestone_count": len(arc.get('key_milestones', []))
            }
        
        except Exception as e:
            logger.error(f"人物弧线设计失败：{e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "message": "人物弧线设计失败"
            }
        
        finally:
            self.state = "idle"
    
    async def prepare_character_states(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        准备章节中的人物状态
        
        输入:
        {
            "chapter_num": 5,
            "appearing_characters": ["char_001", "char_002"],
            "chapter_context": "本章情境"
        }
        
        输出:
        {
            "status": "success",
            "character_states": [
                {
                    "character_id": "char_001",
                    "current_location": "地点",
                    "emotional_state": "情绪",
                    "current_goal": "当前目标",
                    "relevant_relationships": [...],
                    "recent_events": ["最近事件"]
                }
            ]
        }
        """
        chapter_num = task.get('chapter_num')
        appearing_characters = task.get('appearing_characters', [])
        chapter_context = task.get('chapter_context', '')
        
        logger.info(f"准备人物状态：第{chapter_num}章，{len(appearing_characters)}个人物")
        self.state = "working"
        self.last_active = datetime.now()
        
        try:
            character_states = []
            
            for char_id in appearing_characters:
                # 获取人物信息
                if self.memory_engine:
                    char_data = await self.memory_engine.retrieve({
                        "type": "character",
                        "character_id": char_id
                    })
                else:
                    char_data = {}
                
                # 构建状态
                state = {
                    "character_id": char_id,
                    "chapter_num": chapter_num,
                    "current_location": char_data.get('last_location', '未知'),
                    "emotional_state": 'neutral',
                    "current_goal": char_data.get('current_goal', ''),
                    "relevant_relationships": [],
                    "recent_events": []
                }
                
                character_states.append(state)
            
            return {
                "status": "success",
                "character_states": character_states,
                "character_count": len(character_states)
            }
        
        except Exception as e:
            logger.error(f"人物状态准备失败：{e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "message": "人物状态准备失败"
            }
        
        finally:
            self.state = "idle"
    
    # ========== 辅助方法 ==========
    
    def _build_create_character_prompt(
        self,
        name: str,
        role: str,
        story_context: str,
        requirements: Dict
    ) -> str:
        """构建人物创建 Prompt"""
        return f"""请创建一个人物设定。

## 基本信息
- 姓名：{name}
- 角色类型：{role}
- 故事背景：{story_context}

## 额外要求
{requirements}

## 设计要求
请创建一个立体、真实的人物，包含以下维度：

### 1. 外在特征
- 外貌描写（年龄、身高、体型、五官、穿着风格）
- 标志性特征（让人印象深刻的点）

### 2. 内在特征
- 性格特点（至少 3 个，包含矛盾点）
- 价值观和信念
- 恐惧和弱点
- 欲望和目标

### 3. 背景故事
- 成长经历
- 重要事件
- 人际关系

### 4. 行为特征
- 说话方式（口头禅、语速、用词习惯）
- 行为习惯
- 决策模式

### 5. 成长潜力
- 可能的成长方向
- 需要克服的缺陷

## 输出格式
{{
    "name": "{name}",
    "role": "{role}",
    "appearance": {{
        "age": 25,
        "height": "180cm",
        "build": "修长",
        "features": ["特征 1", "特征 2"],
        "style": "穿着风格"
    }},
    "personality": {{
        "traits": ["性格 1", "性格 2", "性格 3"],
        "strengths": ["优点 1", "优点 2"],
        "weaknesses": ["缺点 1", "缺点 2"],
        "fears": ["恐惧"],
        "values": ["价值观"]
    }},
    "background": {{
        "origin": "出身",
        "key_events": ["事件 1", "事件 2"],
        "relationships": ["重要关系"]
    }},
    "goals": {{
        "short_term": "短期目标",
        "long_term": "长期目标",
        "motivation": "动机"
    }},
    "dialogue_style": {{
        "speech_pattern": "说话模式",
        "catchphrases": ["口头禅"],
        "tone": "语气特点"
    }},
    "arc_potential": {{
        "starting_point": "起始状态",
        "potential_growth": "成长方向",
        "internal_conflict": "内心冲突"
    }}
}}

请确保人物立体、有魅力、有成长空间。"""
    
    def _build_relationship_design_prompt(
        self,
        characters: List[str],
        story_context: str,
        relationship_types: List[str]
    ) -> str:
        """构建关系设计 Prompt"""
        return f"""请设计人物关系网络。

## 人物列表
{characters}

## 故事背景
{story_context}

## 关系类型
{relationship_types}

## 设计要求
1. 关系要多样化（朋友、敌人、恋人、家人、师徒等）
2. 关系要有历史渊源
3. 关系要有动态变化潜力
4. 关系要有冲突点

## 输出格式
[
    {{
        "character_1": "char_001",
        "character_2": "char_002",
        "type": "friend",
        "description": "关系描述（100-200 字）",
        "strength": 8,
        "history": "关系历史",
        "dynamics": "互动模式",
        "conflicts": ["潜在冲突点"],
        "evolution": "可能的演变方向"
    }}
]

请创建 3-5 个有意义的关系。"""
    
    def _build_consistency_check_prompt(
        self,
        character: Dict,
        chapter_content: str,
        character_actions: List[str]
    ) -> str:
        """构建一致性检查 Prompt"""
        return f"""请检查人物行为一致性。

## 人物设定
{character}

## 章节内容
{chapter_content[:6000]}

## 人物行动
{character_actions}

## 检查维度
1. **性格一致性**: 行动是否符合性格设定
2. **动机一致性**: 行动是否有合理动机
3. **对话一致性**: 对话是否符合说话方式
4. **目标一致性**: 行动是否服务于目标
5. **成长连续性**: 是否有突兀的变化

## 输出格式
{{
    "consistent": true/false,
    "issues": [
        {{
            "type": "personality/behavior/dialogue/goal/growth",
            "description": "问题描述",
            "severity": "low/medium/high",
            "location": "问题位置",
            "suggestion": "修改建议"
        }}
    ],
    "suggestions": ["总体建议"]
}}

请仔细检查，确保人物不 OOC。"""
    
    def _build_character_arc_prompt(
        self,
        character_id: str,
        story_span: str,
        theme: str
    ) -> str:
        """构建人物弧线 Prompt"""
        return f"""请设计人物成长弧线。

## 人物 ID
{character_id}

## 故事跨度
{story_span}

## 主题
{theme}

## 设计要求
人物弧线应该:
1. 有清晰的起点和终点
2. 有关键转折事件
3. 有内心挣扎和成长
4. 与故事主题呼应

## 输出格式
{{
    "starting_state": {{
        "description": "起始状态描述",
        "beliefs": ["初始信念"],
        "flaws": ["初始缺陷"],
        "goals": ["初始目标"]
    }},
    "ending_state": {{
        "description": "最终状态描述",
        "beliefs": ["最终信念"],
        "growth": ["成长点"],
        "achievements": ["成就"]
    }},
    "key_milestones": [
        {{
            "chapter": 10,
            "event": "转折事件 1",
            "impact": "对人物的影响",
            "change": "产生的变化"
        }},
        {{
            "chapter": 30,
            "event": "转折事件 2",
            "impact": "对人物的影响",
            "change": "产生的变化"
        }},
        {{
            "chapter": 50,
            "event": "中点觉醒",
            "impact": "对人物的影响",
            "change": "产生的变化"
        }}
    ],
    "internal_change": "内心变化描述（100-200 字）",
    "external_change": "外在变化描述（100-200 字）",
    "arc_type": "positive/negative/flat"
}}

请设计一个完整、动人的人物成长弧线。"""
    
    def _parse_json(self, text: str) -> Optional[Dict]:
        """解析 JSON 结果"""
        import json
        try:
            start = text.find('{')
            end = text.rfind('}') + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
        except Exception as e:
            logger.warning(f"JSON 解析失败：{e}")
        return None
    
    def _parse_json_list(self, text: str) -> List[Dict]:
        """解析 JSON 列表结果"""
        import json
        try:
            start = text.find('[')
            end = text.rfind(']') + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
        except Exception as e:
            logger.warning(f"JSON 列表解析失败：{e}")
        return []
