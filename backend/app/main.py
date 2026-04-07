# ==========================================
# 多 Agent 协作小说系统 - FastAPI 主入口
# ==========================================

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import sys
from pathlib import Path

# 导入配置
from app.config import get_config_manager, reload_config
from app.services.config_service import get_config_service
from app.exceptions import register_exception_handlers

# 导入 Agent 注册
from app.agents.registry import create_agents

# 导入路由
from app.api import router as api_router
from app.api.responses import install_exception_handlers
from app.api import ws_routes

# 修复 Windows 终端中文乱码
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# 配置日志
# 确保日志目录存在
log_dir = Path('./logs')
log_dir.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(log_dir / 'app.log', encoding='utf-8', mode='a')
    ]
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    """
    # 启动时执行
    logger.info("=" * 60)
    logger.info("多 Agent 协作小说系统 v1.0.0 启动中...")
    logger.info("=" * 60)
    
    # 创建必要的目录
    data_dirs = [
        "./data/vector_db",
        "./data/knowledge_graph",
        "./data/styles",
        "./data/fused_styles",
        "./data/schools",
        "./logs",
        "./backups",
        "./projects",
        "./backend/config"
    ]
    for dir_path in data_dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
    
    # 加载配置
    try:
        config = get_config_manager()
        logger.info(f"[OK] 配置加载成功：{config.app_config.project_name if config.app_config else '默认项目'}")
        runtime_config = get_config_service().get_runtime_config(mask_secrets=True)
        logger.info(f"   默认 LLM 提供商：{runtime_config.get('default_provider') or '未配置'}")
        logger.info(f"   已配置提供商：{list(runtime_config.get('providers', {}).keys())}")
    except Exception as e:
        logger.error(f"[FAIL] 配置加载失败：{e}")
    
    # 初始化所有 Agent
    try:
        create_agents({})
        logger.info(f"[OK] 所有 Agent 已初始化")
    except Exception as e:
        logger.error(f"[FAIL] Agent 初始化失败：{e}")
    
    logger.info("=" * 60)
    logger.info("[SUCCESS] 系统启动完成！")
    logger.info(f"   API 文档：http://localhost:8000/docs")
    logger.info(f"   健康检查：http://localhost:8000/api/health")
    logger.info("=" * 60)
    
    yield
    
    # 关闭时执行
    logger.info("系统关闭中...")
    logger.info("系统已关闭")


# 创建 FastAPI 应用
app = FastAPI(
    title="多 Agent 协作小说系统",
    description="""
## 功能特性

- **7 大 Agent 协作**: 主编、剧情、人物、写手、对话、审核、学习
- **三层记忆系统**: 短期 + 中期 + 长期记忆
- **四层学习记忆**: 原始→模式→技巧→风格
- **派系分类系统**: 按类型/文笔/节奏分类，支持融合
- **可配置 LLM**: 火山/阿里云/eggfans 完全可配置
- **本地保存**: 自动保存 + Git 版本控制

## API 分类

- **配置管理**: `/api/config` - 项目配置和 LLM 配置
- **健康检查**: `/api/health` - 系统健康状态
- **Agent 管理**: `/api/agents` - Agent 状态和任务执行
- **写作流程**: `/api/writing` - 章节创作和工作流
- **学习系统**: `/api/learning` - 作品学习和风格分析
- **派系管理**: `/api/schools` - 派系统管理和融合
    """,
    version="1.0.0",
    lifespan=lifespan
)

install_exception_handlers(app)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册异常处理器
register_exception_handlers(app)

# 注册路由
app.include_router(api_router)
app.include_router(ws_routes.router)


# 根路径
@app.get("/")
async def root():
    """
    根路径 - 系统信息
    """
    return {
        "name": "多 Agent 协作小说系统",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
        "health": "/api/health"
    }


# 配置重新加载端点
@app.post("/api/config/reload")
async def reload_configuration():
    """
    重新加载配置（热更新）
    """
    try:
        changed = reload_config()
        if changed:
            return {
                "status": "success",
                "message": "配置已重新加载"
            }
        else:
            return {
                "status": "success",
                "message": "配置无变更"
            }
    except Exception as e:
        logger.error(f"配置重新加载失败：{e}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": str(e)}
        )


# 测试端点
@app.get("/api/ping")
async def ping():
    """
    测试端点 - 检查 API 是否可达
    """
    return {"status": "pong", "timestamp": "2026-03-21T18:00:00"}


# 主程序入口
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
