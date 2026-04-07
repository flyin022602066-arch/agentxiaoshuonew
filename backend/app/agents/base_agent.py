# ==========================================
# 多 Agent 协作小说系统 - Agent 基类
# ==========================================

from typing import Dict, Any, Optional
from datetime import datetime


class BaseAgent:
    """
    所有 Agent 的基类
    
    属性:
        agent_id: Agent 唯一标识
        config: 配置字典
        llm_client: LLM 客户端实例
        memory_engine: 记忆引擎实例
        state: 当前状态 (idle/working/error)
        last_active: 最后活跃时间
    """
    
    def __init__(self, agent_id: str, config: Dict[str, Any]):
        self.agent_id = agent_id
        self.config = config
        self.llm_client = config.get('llm_client')
        self.memory_engine = config.get('memory_engine')
        self.state = "idle"
        self.last_active: Optional[datetime] = None
    
    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """执行任务 - 子类实现"""
        raise NotImplementedError
    
    def get_system_prompt(self) -> str:
        """获取系统 Prompt - 子类实现"""
        raise NotImplementedError
    
    def log(self, message: str, level: str = "info"):
        """日志输出"""
        import logging
        logger = logging.getLogger(self.agent_id)
        getattr(logger, level)(f"[{self.agent_id}] {message}")

    async def call_llm(self, prompt: str, **kwargs) -> str:
        """统一的 LLM 调用入口。"""
        if not self.llm_client:
            raise RuntimeError(f"{self.agent_id} 未配置 llm_client")
        return await self.llm_client.generate(prompt, self.get_system_prompt(), **kwargs)
