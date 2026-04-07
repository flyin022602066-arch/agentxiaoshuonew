# ==========================================
# 多 Agent 协作小说系统 - Celery 任务编排
# ==========================================

from celery import Celery, chain, group
from datetime import datetime
from typing import Dict, Any, List
import logging
import asyncio

logger = logging.getLogger(__name__)

# Celery 配置
celery_app = Celery(
    'novel_agents',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0'
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Shanghai',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
    task_soft_time_limit=3300,
)


@celery_app.task(bind=True, max_retries=3)
def agent_execute_task(self, agent_id: str, task: Dict[str, Any]) -> Dict[str, Any]:
    """Agent 执行任务"""
    try:
        from app.agents.registry import get_agent
        
        agent = get_agent(agent_id)
        if not agent:
            raise ValueError(f"Agent 未找到：{agent_id}")
        
        result = asyncio.run(agent.execute(task))
        
        return {
            "status": "success",
            "agent_id": agent_id,
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Agent 任务执行失败：{e}")
        raise self.retry(exc=e, countdown=60)


@celery_app.task
def start_chapter_workflow(chapter_num: int, project_id: str, outline: str) -> Dict[str, Any]:
    """
    章节创作工作流
    
    流程:
    1. 剧情架构师 → 细化大纲
    2. 人物设计师 → 准备角色状态
    3. 章节写手 → 撰写初稿
    4. 对话专家 → 打磨对话
    5. 审核编辑 → 一致性检查
    6. 主编 → 最终审核
    """
    
    # 并行准备：剧情 + 人物
    prep_group = group(
        agent_execute_task.s('plot_agent', {
            'action': 'refine_chapter_outline',
            'chapter_num': chapter_num,
            'outline': outline
        }),
        agent_execute_task.s('character_agent', {
            'action': 'prepare_character_states',
            'chapter_num': chapter_num
        })
    )
    
    # 串行流程：写→改→审→主编
    workflow_chain = chain(
        prep_group,
        agent_execute_task.s('writer_agent', {
            'action': 'write_chapter',
            'chapter_num': chapter_num,
            'outline': outline
        }),
        agent_execute_task.s('dialogue_agent', {
            'action': 'polish_dialogue'
        }),
        agent_execute_task.s('reviewer_agent', {
            'action': 'consistency_check'
        }),
        agent_execute_task.s('editor_agent', {
            'action': 'final_review'
        })
    )
    
    result = workflow_chain.apply_async()
    
    return {
        "workflow_id": result.id,
        "status": "started",
        "chapter_num": chapter_num
    }


@celery_app.task
def get_workflow_status(workflow_id: str) -> Dict[str, Any]:
    """查询工作流状态"""
    from celery.result import AsyncResult
    
    result = AsyncResult(workflow_id)
    
    return {
        "workflow_id": workflow_id,
        "status": result.status,
        "result": result.result if result.ready() else None,
        "progress": 100 if result.ready() else 0
    }
