# ==========================================
# 多 Agent 协作小说系统 - 健康检查端点
# ==========================================

from fastapi import APIRouter, HTTPException
from typing import Any, Awaitable, Dict, List, TypeAlias, cast
from datetime import datetime
import inspect
import logging

from app.services.config_service import get_config_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["健康检查"])


# ========== 健康检查数据结构 ==========

class HealthStatus(str):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"


CheckResult: TypeAlias = Dict[str, Any]
HealthReport: TypeAlias = Dict[str, Any]


# ========== 检查函数 ==========

async def check_database() -> CheckResult:
    """检查 SQLite 数据库"""
    try:
        import aiosqlite
        from app.novel_db import get_default_novel_db_path

        db_path = str(get_default_novel_db_path())
        
        async with aiosqlite.connect(db_path) as db:
            await db.execute("SELECT 1")
            await db.commit()
        
        return {
            "status": "ok",
            "path": db_path,
            "message": "数据库连接正常"
        }
    except Exception as e:
        logger.error(f"数据库检查失败：{e}")
        return {
            "status": "error",
            "error": str(e),
            "message": "数据库连接失败"
        }


async def check_redis() -> CheckResult:
    """检查 Redis 连接"""
    try:
        import redis.asyncio as redis
        from app.config import get_config_manager
        
        config = get_config_manager()
        redis_url = config.app_config.redis_url if config.app_config else "redis://localhost:6379/0"
        
        r = redis.from_url(redis_url, socket_timeout=5)
        ping_result = r.ping()
        if inspect.isawaitable(ping_result):
            await cast(Awaitable[Any], ping_result)
        close_result = r.close()
        if inspect.isawaitable(close_result):
            await cast(Awaitable[Any], close_result)
        
        return {
            "status": "ok",
            "url": redis_url,
            "message": "Redis 连接正常"
        }
    except ImportError:
        logger.warning("redis 依赖未安装，跳过 Redis 检查")
        return {
            "status": "warning",
            "message": "redis 依赖未安装，跳过 Redis 检查"
        }
    except Exception as e:
        logger.warning(f"Redis 检查失败：{e}")
        return {
            "status": "warning",
            "error": str(e),
            "message": "Redis 未启动或不可达（不影响本地核心写作功能）"
        }


async def check_vector_db() -> CheckResult:
    """检查向量数据库"""
    try:
        from pathlib import Path
        from app.config import get_config_manager
        
        config = get_config_manager()
        db_path = config.memory_config.vector_db_path if config.memory_config else "./data/vector_db"
        
        path = Path(db_path)
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
        
        return {
            "status": "ok",
            "path": str(path),
            "exists": True,
            "message": "向量数据库目录正常"
        }
    except Exception as e:
        logger.error(f"向量数据库检查失败：{e}")
        return {
            "status": "error",
            "error": str(e),
            "message": "向量数据库检查失败"
        }


async def check_llm_providers() -> List[CheckResult]:
    """检查所有 LLM 提供商配置"""
    results = []
    
    try:
        config = get_config_service().get_runtime_config(mask_secrets=True)
        providers = config.get("providers", {})

        for provider_name, provider in providers.items():
            configured = bool(provider.get("has_api_key")) and bool(provider.get("base_url")) and bool(provider.get("model"))
            result = {
                "provider": provider_name,
                "status": "ok" if configured and provider.get("enabled", True) else "error",
                "configured": configured,
                "has_api_key": provider.get("has_api_key", False),
            }
            if not configured:
                result["error"] = "配置不完整"
            results.append(result)

        if not providers:
            results.append({
                "status": "warning",
                "message": "未配置任何 LLM 提供商"
            })
        
    except Exception as e:
        logger.error(f"LLM 提供商检查失败：{e}")
        results.append({
            "status": "error",
            "error": str(e),
            "message": "LLM 提供商检查失败"
        })
    
    return results


async def check_celery() -> CheckResult:
    """检查 Celery Worker"""
    try:
        from app.tasks.celery_app import celery_app

        if celery_app is None:
            return {
                "status": "warning",
                "message": "Celery 未配置，跳过 Worker 检查"
            }
        
        # 尝试获取 Worker 状态
        inspect = celery_app.control.inspect()
        active_workers = inspect.active()
        
        if active_workers:
            return {
                "status": "ok",
                "workers": len(active_workers),
                "message": f"Celery Worker 运行正常 ({len(active_workers)} 个)"
            }
        else:
            return {
                "status": "warning",
                "message": "未检测到活跃的 Celery Worker"
            }
    except Exception as e:
        logger.warning(f"Celery 检查失败：{e}")
        return {
            "status": "warning",
            "error": str(e),
            "message": "Celery 未启动或当前环境未启用"
        }


async def check_disk_space() -> CheckResult:
    """检查磁盘空间"""
    try:
        import shutil
        
        # 检查工作目录磁盘空间
        total, used, free = shutil.disk_usage(".")
        free_gb = free / (1024 ** 3)
        usage_percent = (used / total) * 100
        
        status = "ok" if free_gb > 1 else "warning" if free_gb > 0.5 else "error"
        
        return {
            "status": status,
            "total_gb": round(total / (1024 ** 3), 2),
            "used_gb": round(used / (1024 ** 3), 2),
            "free_gb": round(free_gb, 2),
            "usage_percent": round(usage_percent, 2),
            "message": f"剩余空间 {free_gb:.2f} GB"
        }
    except Exception as e:
        logger.error(f"磁盘空间检查失败：{e}")
        return {
            "status": "error",
            "error": str(e),
            "message": "磁盘空间检查失败"
        }


async def check_memory_usage() -> CheckResult:
    """检查内存使用"""
    try:
        import psutil
        import os

        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()

        memory_mb = memory_info.rss / (1024 ** 2)
        memory_percent = process.memory_percent()

        status = "ok" if memory_percent < 80 else "warning" if memory_percent < 90 else "error"

        return {
            "status": status,
            "memory_mb": round(memory_mb, 2),
            "memory_percent": round(memory_percent, 2),
            "message": f"内存使用 {memory_mb:.2f} MB ({memory_percent:.1f}%)"
        }
    except ImportError:
        # psutil is optional in some environments; skip this check gracefully
        logger.warning("psutil 未安装，跳过内存检查")
        return {
            "status": "warning",
            "message": "psutil 未安装，跳过内存检查"
        }
    except Exception as e:
        logger.error(f"内存使用检查失败：{e}")
        return {
            "status": "error",
            "error": str(e),
            "message": "内存使用检查失败"
        }


async def check_agents() -> List[CheckResult]:
    """检查 Agent 状态"""
    results = []
    
    try:
        from app.agents.registry import get_agent, AgentRegistry
        
        registry = AgentRegistry()
        agents = registry.get_all()
        
        for agent_id, agent in agents.items():
            result = {
                "agent_id": agent_id,
                "status": "ok" if agent.state == "idle" else "busy",
                "state": agent.state,
                "last_active": agent.last_active.isoformat() if agent.last_active else None
            }
            results.append(result)
        
        if not agents:
            results.append({
                "status": "warning",
                "message": "未注册任何 Agent"
            })
        
    except Exception as e:
        logger.error(f"Agent 检查失败：{e}")
        results.append({
            "status": "error",
            "error": str(e),
            "message": "Agent 检查失败"
        })
    
    return results


# ========== API 端点 ==========

@router.get("")
async def health_check(detailed: bool = False):
    """
    系统健康检查
    
    - **detailed**: 是否返回详细检查结果
    """
    start_time = datetime.now()
    
    # 基础检查（总是执行）
    checks = {
        "timestamp": start_time.isoformat(),
        "status": HealthStatus.HEALTHY,
        "checks": {}
    }
    
    # 数据库检查
    checks["checks"]["database"] = await check_database()
    
    # 向量数据库检查
    checks["checks"]["vector_db"] = await check_vector_db()
    
    # LLM 提供商检查
    checks["checks"]["llm_providers"] = await check_llm_providers()
    
    # 如果请求详细检查
    if detailed:
        # Redis 检查
        checks["checks"]["redis"] = await check_redis()
        
        # Celery 检查
        checks["checks"]["celery"] = await check_celery()
        
        # 磁盘空间检查
        checks["checks"]["disk_space"] = await check_disk_space()
        
        # 内存使用检查
        checks["checks"]["memory"] = await check_memory_usage()
        
        # Agent 状态检查
        checks["checks"]["agents"] = await check_agents()
    
    # 计算整体状态
    all_checks = list(checks["checks"].values())
    
    # 展平嵌套列表（llm_providers 和 agents 返回列表）
    flat_checks = []
    for check in all_checks:
        if isinstance(check, list):
            flat_checks.extend(check)
        else:
            flat_checks.append(check)
    
    error_count = sum(1 for c in flat_checks if c.get("status") == "error")
    warning_count = sum(1 for c in flat_checks if c.get("status") == "warning")
    
    if error_count > 0:
        checks["status"] = HealthStatus.UNHEALTHY
    elif warning_count > 0:
        checks["status"] = HealthStatus.DEGRADED
    
    # 添加统计信息
    checks["summary"] = {
        "total_checks": len(flat_checks),
        "healthy": sum(1 for c in flat_checks if c.get("status") == "ok"),
        "warnings": warning_count,
        "errors": error_count,
        "check_duration_ms": (datetime.now() - start_time).total_seconds() * 1000
    }
    
    return checks


@router.get("/ready")
async def readiness_check():
    """
    就绪检查
    用于 Kubernetes 等容器的就绪探针
    """
    # 检查关键服务是否可用
    db_check = await check_database()
    vector_db_check = await check_vector_db()
    
    if db_check["status"] == "ok" and vector_db_check["status"] == "ok":
        return {"status": "ready", "message": "服务就绪"}
    else:
        raise HTTPException(
            status_code=503,
            detail="服务未就绪",
            headers={"Retry-After": "30"}
        )


@router.get("/live")
async def liveness_check():
    """
    存活检查
    用于 Kubernetes 等容器的存活探针
    """
    # 简单检查进程是否存活
    return {"status": "alive", "timestamp": datetime.now().isoformat()}


@router.get("/metrics")
async def metrics():
    """
    性能指标
    返回 Prometheus 格式的指标数据
    """
    try:
        import psutil
        import os
        process = psutil.Process(os.getpid())
        metrics = {
            "process_cpu_percent": process.cpu_percent(),
            "process_memory_mb": process.memory_info().rss / (1024 ** 2),
            "process_memory_percent": process.memory_percent(),
            "timestamp": datetime.now().isoformat()
        }
        return metrics
    except ImportError:
        logger.warning("psutil 未安装，metrics 将跳过")
        return {
            "process_cpu_percent": None,
            "process_memory_mb": None,
            "process_memory_percent": None,
            "timestamp": datetime.now().isoformat(),
            "note": "psutil 未安装，无法收集指标"
        }
