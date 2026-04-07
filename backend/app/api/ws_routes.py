# ==========================================
# 多 Agent 协作小说系统 - WebSocket 路由
# ==========================================

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional
import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

router = APIRouter(tags=["WebSocket"])


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: Optional[str] = Query(None)
):
    """
    WebSocket 端点 - 支持实时通信
    """
    from app.api.websocket import get_connection_manager, get_agent_broadcaster

    manager = get_connection_manager()
    broadcaster = get_agent_broadcaster()

    if not client_id:
        client_id = str(uuid.uuid4())

    await websocket.accept()
    await manager.connect(websocket, client_id)

    await broadcaster.broadcast_log(
        level="info",
        message=f"用户 {client_id} 连接",
        agent_id="system"
    )

    try:
        await websocket.send_json({
            "type": "connected",
            "data": {
                "client_id": client_id,
                "message": "连接成功",
                "timestamp": datetime.now().isoformat()
            }
        })

        while True:
            data = await websocket.receive_json()

            msg_type = data.get('type')
            msg_data = data.get('data', {})

            if msg_type == 'subscribe':
                topic = msg_data.get('topic', 'global')
                manager.subscribe(client_id, topic)
                await websocket.send_json({
                    "type": "subscribed",
                    "data": {
                        "topic": topic,
                        "timestamp": datetime.now().isoformat()
                    }
                })

            elif msg_type == 'unsubscribe':
                topic = msg_data.get('topic', 'global')
                manager.unsubscribe(client_id, topic)
                await websocket.send_json({
                    "type": "unsubscribed",
                    "data": {
                        "topic": topic,
                        "timestamp": datetime.now().isoformat()
                    }
                })

            elif msg_type == 'ping':
                await websocket.send_json({
                    "type": "pong",
                    "data": {
                        "timestamp": datetime.now().isoformat()
                    }
                })

            elif msg_type == 'get_agent_status':
                from app.agents.registry import get_agent_status
                status = get_agent_status()
                await websocket.send_json({
                    "type": "agent_status",
                    "data": {
                        "agents": list(status.values()),
                        "timestamp": datetime.now().isoformat()
                    }
                })

            elif msg_type == 'get_task_status':
                task_id = msg_data.get('task_id')
                if task_id:
                    from app.tasks.task_manager import get_task_manager
                    task_manager = get_task_manager()
                    task = task_manager.get_task(task_id)
                    if task:
                        await websocket.send_json({
                            "type": "task_status",
                            "data": {
                                "task": task.to_dict(),
                                "timestamp": datetime.now().isoformat()
                            }
                        })

            elif msg_type == 'send_message':
                target_client = msg_data.get('target_client_id')
                message = msg_data.get('message', {})
                if target_client:
                    await manager.send_personal_message({
                        "type": "message",
                        "data": {
                            "from": client_id,
                            "message": message,
                            "timestamp": datetime.now().isoformat()
                        }
                    }, target_client)

            else:
                await manager.handle_message(client_id, data)

    except WebSocketDisconnect:
        logger.info(f"WebSocket 断开连接：{client_id}")
    except Exception as e:
        logger.error(f"WebSocket 错误：{e}")
    finally:
        await broadcaster.broadcast_log(
            level="info",
            message=f"用户 {client_id} 断开连接",
            agent_id="system"
        )
        await manager.disconnect(client_id)


@router.get("/ws/status")
async def get_websocket_status():
    """获取 WebSocket 状态"""
    from app.api.websocket import get_connection_manager

    manager = get_connection_manager()

    return {
        "status": "success",
        "data": {
            "connections": manager.get_connection_count(),
            "subscribers": {
                "global": manager.get_subscriber_count("global"),
                "agents": manager.get_subscriber_count("agents"),
                "tasks": manager.get_subscriber_count("tasks"),
                "logs": manager.get_subscriber_count("logs")
            }
        }
    }
