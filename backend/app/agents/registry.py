# ==========================================
# 多 Agent 协作小说系统 - Agent 注册表
# ==========================================

from typing import Dict, Any, Optional, Type
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# 延迟导入 BaseAgent
BaseAgent = None

def get_base_agent_class():
    """获取 BaseAgent 类"""
    global BaseAgent
    if BaseAgent is None:
        try:
            from .base_agent import BaseAgent as AgentClass
            BaseAgent = AgentClass
        except ImportError:
            # 如果 base_agent 不存在，使用内联定义
            class SimpleBaseAgent:
                def __init__(self, agent_id: str, config: Dict[str, Any]):
                    self.agent_id = agent_id
                    self.config = config
                    self.llm_client = None
                    self.memory_engine = None
                    self.state = "idle"
                    self.last_active = None
                async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
                    raise NotImplementedError
                def get_system_prompt(self) -> str:
                    raise NotImplementedError
            BaseAgent = SimpleBaseAgent
    return BaseAgent


class AgentRegistry:
    """
    Agent 注册表 - 单例模式
    管理所有 Agent 实例的注册、获取、状态查询
    """
    
    _instance: Optional['AgentRegistry'] = None
    _agents: Dict[str, BaseAgent] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def register(self, agent: BaseAgent):
        """注册一个 Agent 实例"""
        if agent.agent_id in self._agents:
            logger.warning(f"Agent 已存在：{agent.agent_id}")
        else:
            self._agents[agent.agent_id] = agent
            logger.info(f"Agent 已注册：{agent.agent_id}")
    
    def get(self, agent_id: str) -> Optional[BaseAgent]:
        """获取 Agent 实例"""
        agent = self._agents.get(agent_id)
        if agent is None:
            logger.error(f"Agent 未找到：{agent_id}")
        return agent
    
    def get_all(self) -> Dict[str, BaseAgent]:
        """获取所有 Agent"""
        return self._agents.copy()
    
    def get_status(self) -> Dict[str, Dict[str, Any]]:
        """获取所有 Agent 状态（前端监控用）"""
        return {
            agent_id: {
                "agent_id": agent_id,
                "state": agent.state,
                "last_active": agent.last_active.isoformat() if agent.last_active else None,
                "config_summary": self._get_config_summary(agent.config)
            }
            for agent_id, agent in self._agents.items()
        }
    
    def _get_config_summary(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """获取配置摘要（脱敏）"""
        summary = {}
        for key, value in config.items():
            if isinstance(value, str) and 'key' in key.lower():
                # API Key 脱敏
                summary[key] = '***' + value[-4:] if value else ''
            else:
                summary[key] = value
        return summary
    
    def unregister(self, agent_id: str):
        """注销 Agent"""
        if agent_id in self._agents:
            del self._agents[agent_id]
            logger.info(f"Agent 已注销：{agent_id}")
    
    def clear(self):
        """清空所有 Agent"""
        self._agents.clear()
        logger.info("所有 Agent 已清空")


# ========== 全局注册表实例 ==========

registry = AgentRegistry()


def get_agent(agent_id: str) -> Optional[BaseAgent]:
    """快速获取 Agent 实例"""
    return registry.get(agent_id)


def get_all_agents() -> Dict[str, BaseAgent]:
    """获取所有 Agent"""
    return registry.get_all()


def set_agent_state(agent_id: str, state: str):
    """设置 Agent 状态"""
    agent = registry.get(agent_id)
    if agent:
        agent.state = state
        from datetime import datetime
        agent.last_active = datetime.now()


def get_agent_status() -> Dict[str, Dict[str, Any]]:
    """获取所有 Agent 状态"""
    return registry.get_status()


def register_agent(agent: BaseAgent):
    """注册 Agent"""
    registry.register(agent)


# ========== Agent 工厂函数 ==========

def create_agents(config: Dict[str, Any]):
    """
    创建并注册所有 7 大 Agent 实例
    
    Args:
        config: 包含 llm_client 和 memory_engine 的配置字典
    """
    from app.utils.llm_client import get_llm_client
    from app.memory.memory_engine import get_memory_engine
    
    BaseAgent = get_base_agent_class()
    
    try:
        # 导入所有 7 大 Agent
        from .learning_agent import LearningAgent
        from .writer_agent import WriterAgent
        from .plot_agent import PlotAgent
        from .character_agent import CharacterAgent
        from .dialogue_agent import DialogueAgent
        from .reviewer_agent import ReviewerAgent
        from .editor_agent import EditorAgent
        
        llm_client = get_llm_client()
        memory_engine = get_memory_engine()
        
        agent_config = {
            'llm_client': llm_client,
            'memory_engine': memory_engine,
            'project_config': config
        }
        
        # 注册所有 7 大 Agent
        registry.register(LearningAgent('learning_agent', agent_config))
        registry.register(WriterAgent('writer_agent', agent_config))
        registry.register(PlotAgent('plot_agent', agent_config))
        registry.register(CharacterAgent('character_agent', agent_config))
        registry.register(DialogueAgent('dialogue_agent', agent_config))
        registry.register(ReviewerAgent('reviewer_agent', agent_config))
        registry.register(EditorAgent('editor_agent', agent_config))
        
        logger.info(f"[OK] 所有 7 大 Agent 已注册")
        logger.info(f"   1. LearningAgent - 学习分析师")
        logger.info(f"   2. PlotAgent - 剧情架构师")
        logger.info(f"   3. CharacterAgent - 人物设计师")
        logger.info(f"   4. WriterAgent - 章节写手")
        logger.info(f"   5. DialogueAgent - 对话专家")
        logger.info(f"   6. ReviewerAgent - 审核编辑")
        logger.info(f"   7. EditorAgent - 主编")
    except Exception as e:
        logger.warning(f"[WARN] Agent 初始化失败：{e}，使用简化模式")
        # 不抛出异常，允许系统继续运行
    
    return registry
