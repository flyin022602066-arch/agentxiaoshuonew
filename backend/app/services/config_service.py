import json
import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional

from app.config_db import ConfigDatabase
from app.exceptions import ConfigError, LLMConfigError

logger = logging.getLogger(__name__)


class ConfigService:
    def __init__(self, db_path: str | Path | None = None, legacy_json_path: str | Path | None = None):
        resolved_db_path = str(db_path) if db_path else None
        self.db = ConfigDatabase() if resolved_db_path is None else ConfigDatabase(resolved_db_path)
        self._uses_default_db_path = db_path is None
        self.legacy_json_path = (
            Path(legacy_json_path)
            if legacy_json_path is not None
            else Path(__file__).resolve().parents[2] / "config" / "llm_providers.json"
        )
        self._migrate_legacy_if_needed()

    def _mask_provider(self, provider: Dict[str, Any]) -> Dict[str, Any]:
        data = dict(provider)
        api_key = data.get("api_key") or ""
        data["has_api_key"] = bool(api_key)
        data["masked_api_key"] = f"***{api_key[-4:]}" if api_key else ""
        data["api_key"] = ""
        data.pop("timeout", None)
        return data

    def _normalize_provider(self, name: str, provider: Dict[str, Any], existing: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        existing = existing or {}
        clear_api_key = provider.get("clear_api_key", False)
        raw_api_key = provider.get("api_key", "")
        if clear_api_key:
            api_key = ""
        elif raw_api_key == "" and (provider.get("has_api_key") or existing.get("api_key")):
            api_key = existing.get("api_key", "")
        else:
            api_key = raw_api_key

        normalized = {
            "name": name,
            "api_format": provider.get("api_format", existing.get("api_format", "openai")),
            "api_key": api_key,
            "base_url": provider.get("base_url", existing.get("base_url", "")),
            "endpoint": provider.get("endpoint", existing.get("endpoint", "/v1/chat/completions")),
            "model": provider.get("model", existing.get("model", "")),
            "auth_type": provider.get("auth_type", existing.get("auth_type", "bearer")),
            "auth_header": provider.get("auth_header", existing.get("auth_header")),
            "headers": provider.get("headers", existing.get("headers", {})),
            "timeout": existing.get("timeout", 60),
            "response_format": provider.get("response_format", existing.get("response_format", "openai")),
            "response_path": provider.get("response_path", existing.get("response_path")),
            "enabled": provider.get("enabled", existing.get("enabled", True)),
            "rate_limit": provider.get("rate_limit", existing.get("rate_limit")),
        }
        return normalized

    def _migrate_legacy_if_needed(self) -> None:
        if not self._uses_default_db_path and self.legacy_json_path == Path(__file__).resolve().parents[2] / "config" / "llm_providers.json":
            return
        if self.db.get_all_providers():
            return
        if not self.legacy_json_path.exists():
            return
        try:
            payload = json.loads(self.legacy_json_path.read_text(encoding="utf-8"))
            providers = payload.get("providers", {})
            if not providers:
                return
            self.save_runtime_config(
                default_provider=payload.get("default_provider", ""),
                providers=providers,
                project_config=self.db.get_project_config(),
            )
            logger.info("Migrated legacy JSON config into SQLite")
        except Exception as exc:
            logger.warning(f"Legacy config migration skipped: {exc}")

    def get_runtime_config(self, mask_secrets: bool = True) -> dict:
        providers = {}
        for row in self.db.get_all_providers():
            providers[row["name"]] = self._mask_provider(row) if mask_secrets else row
        return {
            "default_provider": self.db.get_default_provider(),
            "providers": providers,
            "project_config": self.db.get_project_config(),
        }

    def get_provider_config(self, provider_name: str, mask_secrets: bool = True) -> dict | None:
        provider = self.db.get_provider(provider_name)
        if not provider:
            return None
        return self._mask_provider(provider) if mask_secrets else provider

    def validate_provider_payload(self, provider_name: str, payload: dict) -> dict:
        errors = []
        if payload.get("enabled", True):
            if not payload.get("clear_api_key") and not (payload.get("api_key") or payload.get("has_api_key")):
                errors.append("API Key 不能为空")
            if not payload.get("base_url", "").startswith(("http://", "https://")):
                errors.append("Base URL 格式不正确")
            if not payload.get("model"):
                errors.append("模型名称不能为空")
        if errors:
            return {"valid": False, "error": f"提供商配置无效：{provider_name}", "errors": errors}
        return {"valid": True, "message": "配置验证通过"}

    def get_active_provider_config(self) -> dict | None:
        provider_name = self.db.get_default_provider()
        if not provider_name:
            return None
        provider = self.db.get_provider(provider_name)
        if not provider or not bool(provider.get("enabled", 1)):
            return None
        if not provider.get("api_key") or not provider.get("base_url") or not provider.get("model"):
            return None
        provider["name"] = provider_name
        return provider

    def _save_project_config(self, conn: sqlite3.Connection, config: Dict[str, Any]) -> None:
        conn.execute(
            '''
            UPDATE project_config SET
                project_name = ?,
                project_path = ?,
                default_provider = ?,
                auto_commit = ?,
                git_author_name = ?,
                git_author_email = ?,
                backup_interval = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = 1
            ''',
            (
                config.get("project_name", "我的小说"),
                config.get("project_path", "./projects/我的小说"),
                config.get("default_provider", self.db.get_default_provider()),
                1 if config.get("auto_commit", True) else 0,
                config.get("git_author_name", "Novel Agent"),
                config.get("git_author_email", "novel-agent@local"),
                config.get("backup_interval", 24),
            ),
        )

    def save_runtime_config(self, default_provider: str, providers: dict, project_config: dict) -> dict:
        conn = self.db._get_connection()
        try:
            conn.execute("BEGIN")
            for name, incoming in providers.items():
                existing = self.db.get_provider(name) or {}
                normalized = self._normalize_provider(name, incoming, existing)
                # 验证时使用 normalized 后的数据（已恢复真实 api_key）
                validation = self.validate_provider_payload(name, {
                    **normalized,
                    "has_api_key": bool(normalized.get("api_key")),
                    "clear_api_key": incoming.get("clear_api_key", False),
                })
                if not validation["valid"]:
                    raise LLMConfigError(validation["error"], missing_fields=validation["errors"])
                self.db.save_provider_with_connection(conn, name, normalized)
            if default_provider:
                self.db.set_system_config_with_connection(conn, "default_provider", default_provider, "默认 LLM 提供商")
            if project_config is not None:
                merged_project_config = {**self.db.get_project_config(), **project_config, "default_provider": default_provider or self.db.get_default_provider()}
                self._save_project_config(conn, merged_project_config)
            conn.commit()
            return self.get_runtime_config(mask_secrets=True)
        except LLMConfigError:
            conn.rollback()
            raise
        except Exception as e:
            conn.rollback()
            logger.error(f"保存配置异常：{e}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            conn.close()


_config_service: Optional[ConfigService] = None


def get_config_service() -> ConfigService:
    global _config_service
    if _config_service is None:
        _config_service = ConfigService()
    return _config_service
