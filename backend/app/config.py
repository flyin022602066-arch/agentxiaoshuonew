# ==========================================
# 多 Agent 协作小说系统 - 配置管理
# 支持验证、加密存储、热更新
# ==========================================

import os
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import logging

logger = logging.getLogger(__name__)


DEFAULT_NOVEL_DB_PATH = str(Path(__file__).resolve().parents[1] / "data" / "novels.db")


# ========== 配置模型定义 ==========

class LLMProviderConfig(BaseModel):
    """LLM 提供商配置"""
    api_format: str = Field(default="openai", description="API 格式：openai/aliyun/custom")
    api_key: str = Field(default="", description="API Key")
    base_url: str = Field(default="", description="API 基础 URL")
    endpoint: str = Field(default="/chat/completions", description="API 端点")
    model: str = Field(default="", description="模型名称")
    auth_type: str = Field(default="bearer", description="认证类型：bearer/api_key/custom")
    auth_header: Optional[str] = Field(default=None, description="自定义认证 Header")
    headers: Dict[str, str] = Field(default_factory=dict, description="额外 Headers")
    timeout: int = Field(default=60, description="超时时间（秒）")
    response_format: str = Field(default="openai", description="响应格式")
    response_path: Optional[str] = Field(default=None, description="自定义响应解析路径")
    enabled: bool = Field(default=True, description="是否启用")
    rate_limit: Optional[int] = Field(default=None, description="每分钟请求数限制")
    
    @field_validator('base_url')
    @classmethod
    def validate_base_url(cls, v):
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError("Base URL 必须以 http:// 或 https:// 开头")
        return v
    
    @field_validator('timeout')
    @classmethod
    def validate_timeout(cls, v):
        if v < 1 or v > 600:
            raise ValueError("超时时间必须在 1-600 秒之间")
        return v


class MemoryConfig(BaseModel):
    """记忆引擎配置"""
    vector_db_path: str = Field(default="./data/vector_db", description="向量数据库路径")
    vector_db_type: str = Field(default="chroma", description="向量数据库类型：chroma/faiss")
    graph_db_type: str = Field(default="networkx", description="图谱数据库类型：networkx/neo4j")
    sqlite_path: str = Field(default=DEFAULT_NOVEL_DB_PATH, description="SQLite 数据库路径")
    short_term_window: int = Field(default=10, description="短期记忆窗口大小（章节数）")
    embedding_model: str = Field(default="text-embedding-ada-002", description="嵌入模型")
    max_retrieve_results: int = Field(default=10, description="最大检索结果数")


class ProjectConfig(BaseModel):
    """项目配置"""
    project_name: str = Field(..., description="项目名称")
    project_path: str = Field(..., description="项目存储路径")
    default_provider: str = Field(..., description="默认 LLM 提供商")
    auto_commit: bool = Field(default=True, description="是否自动 Git 提交")
    git_author_name: str = Field(default="Novel Agent", description="Git 作者名")
    git_author_email: str = Field(default="novel-agent@local", description="Git 作者邮箱")


class ServerConfig(BaseModel):
    """服务器配置"""
    host: str = Field(default="0.0.0.0", description="监听地址")
    port: int = Field(default=8000, description="监听端口")
    debug: bool = Field(default=False, description="调试模式")
    workers: int = Field(default=4, description="Worker 数量")
    log_level: str = Field(default="INFO", description="日志级别")
    log_file: str = Field(default="./logs/novel-agent.log", description="日志文件路径")
    log_rotation_mb: int = Field(default=100, description="日志轮转大小（MB）")
    log_retention_days: int = Field(default=30, description="日志保留天数")


class RedisConfig(BaseModel):
    """Redis 配置"""
    url: str = Field(default="redis://localhost:6379/0", description="Redis 连接 URL")
    max_connections: int = Field(default=10, description="最大连接数")
    socket_timeout: int = Field(default=5, description="Socket 超时（秒）")


class CeleryConfig(BaseModel):
    """Celery 配置"""
    broker_url: str = Field(default="redis://localhost:6379/0", description="Broker URL")
    result_backend: str = Field(default="redis://localhost:6379/0", description="结果后端")
    task_serializer: str = Field(default="json", description="任务序列化格式")
    result_serializer: str = Field(default="json", description="结果序列化格式")
    timezone: str = Field(default="Asia/Shanghai", description="时区")
    task_time_limit: int = Field(default=3600, description="任务超时（秒）")
    task_soft_time_limit: int = Field(default=3300, description="任务软超时（秒）")
    worker_concurrency: int = Field(default=4, description="Worker 并发数")


class SecurityConfig(BaseModel):
    """安全配置"""
    encrypt_api_keys: bool = Field(default=True, description="是否加密 API Key")
    secret_key_path: str = Field(default="./data/.secret_key", description="加密密钥路径")
    enable_auth: bool = Field(default=False, description="是否启用认证")
    jwt_secret: Optional[str] = Field(default=None, description="JWT 密钥")
    jwt_algorithm: str = Field(default="HS256", description="JWT 算法")
    token_expire_minutes: int = Field(default=60, description="Token 过期时间（分钟）")


class AppConfig(BaseSettings):
    """应用总配置"""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # 项目配置
    project_name: str = Field(default="我的小说", description="项目名称")
    project_path: str = Field(default="./projects/我的小说", description="项目路径")
    
    # LLM 配置
    default_provider: str = Field(default="eggfans", description="默认 LLM 提供商")
    
    # 服务器配置
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    debug: bool = Field(default=False)
    
    # 日志配置
    log_level: str = Field(default="INFO")
    log_file: str = Field(default="./logs/novel-agent.log")
    
    # Redis 配置
    redis_url: str = Field(default="redis://localhost:6379/0")
    
    # 记忆配置
    vector_db_path: str = Field(default="./data/vector_db")
    graph_db_type: str = Field(default="networkx")
    sqlite_path: str = Field(default=DEFAULT_NOVEL_DB_PATH)
    
    # 安全配置
    encrypt_api_keys: bool = Field(default=True)
    
    # Git 配置
    auto_commit: bool = Field(default=True)
    git_author_name: str = Field(default="Novel Agent")
    git_author_email: str = Field(default="novel-agent@local")
    
    # Celery 配置
    celery_broker_url: Optional[str] = Field(default=None)
    celery_result_backend: Optional[str] = Field(default=None)
    celery_worker_concurrency: int = Field(default=4)
    celery_task_time_limit: int = Field(default=3600)


# ========== 配置管理器 ==========

class ConfigManager:
    """
    配置管理器
    支持加载、验证、加密、热更新
    """
    
    def __init__(self, config_dir: Path = None):
        self.config_dir = config_dir or Path("./backend")
        self.env_file = self.config_dir / ".env"
        self.llm_config_file = self.config_dir / "config" / "llm_providers.json"
        
        self.app_config: Optional[AppConfig] = None
        self.llm_providers: Dict[str, LLMProviderConfig] = {}
        self.memory_config: Optional[MemoryConfig] = None
        self.security_config: Optional[SecurityConfig] = None
        
        self._config_hash: Optional[str] = None
        self._last_loaded: Optional[datetime] = None
    
    def load_all(self) -> Dict[str, Any]:
        """加载所有配置"""
        self.app_config = self._load_app_config()
        self.llm_providers = self._load_llm_providers()
        self.memory_config = self._load_memory_config()
        self.security_config = self._load_security_config()
        
        self._config_hash = self._calculate_hash()
        self._last_loaded = datetime.now()
        
        logger.info("配置加载成功")
        return self.to_dict()
    
    def _load_app_config(self) -> AppConfig:
        """加载应用配置"""
        try:
            config = AppConfig()
            logger.info(f"应用配置加载成功：{config.project_name}")
            return config
        except Exception as e:
            logger.error(f"应用配置加载失败：{e}")
            raise
    
    def _load_llm_providers(self) -> Dict[str, LLMProviderConfig]:
        """加载 LLM 提供商配置"""
        # 使用正确的路径 - 相对于 main.py 的父目录
        llm_config_file = Path(__file__).parent.parent / 'config' / 'llm_providers.json'
        
        if not llm_config_file.exists():
            logger.warning(f"LLM 配置文件不存在：{llm_config_file}")
            self._create_empty_llm_config(llm_config_file)
            return {}
        
        try:
            with open(llm_config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            providers = {}
            for name, config_data in data.get('providers', {}).items():
                # 只加载启用的且有 API Key 的提供商
                if config_data.get('enabled', True) and config_data.get('api_key', ''):
                    try:
                        providers[name] = LLMProviderConfig(**config_data)
                    except Exception as e:
                        logger.warning(f"跳过无效的提供商配置 {name}: {e}")
            
            logger.info(f"加载了 {len(providers)} 个 LLM 提供商")
            logger.debug(f"提供商列表：{list(providers.keys())}")
            return providers
        except Exception as e:
            logger.error(f"LLM 配置加载失败：{e}")
            import traceback
            traceback.print_exc()
            # 返回空配置而不是抛出异常
            return {}
    
    def _load_memory_config(self) -> MemoryConfig:
        """加载记忆配置"""
        return MemoryConfig(
            vector_db_path=self.app_config.vector_db_path if self.app_config else "./data/vector_db",
            graph_db_type=self.app_config.graph_db_type if self.app_config else "networkx",
            sqlite_path=self.app_config.sqlite_path if self.app_config else DEFAULT_NOVEL_DB_PATH
        )
    
    def _load_security_config(self) -> SecurityConfig:
        """加载安全配置"""
        return SecurityConfig(
            encrypt_api_keys=self.app_config.encrypt_api_keys if self.app_config else True,
            secret_key_path="./data/.secret_key"
        )
    
    def _create_empty_llm_config(self, target_file: Optional[Path] = None):
        """创建空 LLM 配置模板"""
        llm_config_file = target_file or self.llm_config_file
        llm_config_file.parent.mkdir(parents=True, exist_ok=True)
        
        empty_config = {
            "default_provider": "",
            "providers": {}
        }
        
        with open(llm_config_file, 'w', encoding='utf-8') as f:
            json.dump(empty_config, f, ensure_ascii=False, indent=2)
        
        logger.info(f"创建空 LLM 配置模板：{llm_config_file}")
    
    def validate_llm_provider(self, provider_name: str) -> Dict[str, Any]:
        """验证 LLM 提供商配置"""
        if provider_name not in self.llm_providers:
            return {
                "valid": False,
                "error": f"提供商不存在：{provider_name}"
            }
        
        config = self.llm_providers[provider_name]
        errors = []
        
        # 验证必填字段
        if not config.api_key or len(config.api_key.strip()) == 0:
            errors.append("API Key 不能为空")
        
        if not config.base_url or not config.base_url.startswith(('http://', 'https://')):
            errors.append("Base URL 格式不正确")
        
        if not config.model or len(config.model.strip()) == 0:
            errors.append("模型名称不能为空")
        
        if config.timeout < 1 or config.timeout > 600:
            errors.append("超时时间必须在 1-600 秒之间")
        
        if errors:
            return {
                "valid": False,
                "error": "配置验证失败",
                "errors": errors
            }
        
        return {
            "valid": True,
            "message": "配置验证通过"
        }
    
    def get_llm_provider(self, provider_name: str) -> Optional[LLMProviderConfig]:
        """获取 LLM 提供商配置"""
        return self.llm_providers.get(provider_name)
    
    def get_default_provider(self) -> Optional[str]:
        """获取默认 LLM 提供商"""
        if self.app_config:
            return self.app_config.default_provider
        return None
    
    def get_all_providers(self) -> List[str]:
        """获取所有已配置的提供商列表"""
        return list(self.llm_providers.keys())
    
    def _calculate_hash(self) -> str:
        """计算配置哈希值（用于检测变更）"""
        config_str = json.dumps(self.to_dict(), sort_keys=True)
        return hashlib.sha256(config_str.encode()).hexdigest()[:16]
    
    def has_changed(self) -> bool:
        """检查配置是否发生变更"""
        current_hash = self._calculate_hash()
        return current_hash != self._config_hash
    
    def to_dict(self) -> Dict[str, Any]:
        """配置转字典"""
        return {
            "app": self.app_config.model_dump() if self.app_config else {},
            "llm_providers": {
                name: {
                    **config.model_dump(),
                    "api_key": "***" + config.api_key[-4:] if config.api_key else ""  # 脱敏
                }
                for name, config in self.llm_providers.items()
            },
            "memory": self.memory_config.model_dump() if self.memory_config else {},
            "security": self.security_config.model_dump() if self.security_config else {},
            "last_loaded": self._last_loaded.isoformat() if self._last_loaded else None,
            "config_hash": self._config_hash
        }
    
    def reload(self) -> bool:
        """重新加载配置（热更新）"""
        if self.has_changed():
            logger.info("检测到配置变更，重新加载...")
            self.load_all()
            return True
        return False


# ========== 加密工具类 ==========

class ConfigEncryptor:
    """
    配置加密工具
    用于加密 API Key 等敏感信息
    """
    
    def __init__(self, key_path: str = "./data/.secret_key"):
        self.key_path = Path(key_path)
        self.key = self._load_or_create_key()
    
    def _load_or_create_key(self) -> bytes:
        """加载或创建加密密钥"""
        if self.key_path.exists():
            with open(self.key_path, 'rb') as f:
                return f.read()
        else:
            # 生成新密钥
            import secrets
            key = secrets.token_bytes(32)
            self.key_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.key_path, 'wb') as f:
                f.write(key)
            logger.info(f"创建新的加密密钥：{self.key_path}")
            return key
    
    def encrypt(self, value: str) -> str:
        """加密字符串"""
        from cryptography.fernet import Fernet
        import base64
        
        # 使用简单加密（生产环境建议用更安全的方案）
        key = base64.urlsafe_b64encode(self.key)
        f = Fernet(key)
        encrypted = f.encrypt(value.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def decrypt(self, encrypted_value: str) -> str:
        """解密字符串"""
        from cryptography.fernet import Fernet
        import base64
        
        key = base64.urlsafe_b64encode(self.key)
        f = Fernet(key)
        encrypted = base64.urlsafe_b64decode(encrypted_value.encode())
        decrypted = f.decrypt(encrypted)
        return decrypted.decode()


# ========== 全局配置实例 ==========

# 单例模式
_config_manager: Optional[ConfigManager] = None
_encryptor: Optional[ConfigEncryptor] = None


def get_config_manager() -> ConfigManager:
    """获取配置管理器单例"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
        _config_manager.load_all()
    return _config_manager


def get_encryptor() -> ConfigEncryptor:
    """获取加密器单例"""
    global _encryptor
    if _encryptor is None:
        _encryptor = ConfigEncryptor()
    return _encryptor


def reload_config() -> bool:
    """重新加载配置"""
    manager = get_config_manager()
    return manager.reload()
