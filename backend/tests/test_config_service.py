import json

import pytest

from app.services.config_service import ConfigService
from app.workflow_executor import WritingWorkflowExecutor


def test_get_config_masks_api_keys(tmp_path):
    service = ConfigService(db_path=tmp_path / "config.db")
    service.save_runtime_config(
        default_provider="eggfans",
        providers={
            "eggfans": {
                "api_key": "sk-secret-12345678",
                "base_url": "https://example.com",
                "model": "deepseek-v3",
            }
        },
        project_config={"project_name": "Demo", "project_path": "./projects/demo"},
    )

    result = service.get_runtime_config(mask_secrets=True)

    assert result["providers"]["eggfans"]["api_key"] == ""
    assert result["providers"]["eggfans"]["has_api_key"] is True
    assert result["providers"]["eggfans"]["masked_api_key"].endswith("5678")


def test_get_active_provider_returns_db_backed_runtime_provider(tmp_path):
    service = ConfigService(db_path=tmp_path / "config.db")
    service.save_runtime_config(
        default_provider="eggfans",
        providers={
            "eggfans": {
                "api_key": "sk-live-value",
                "base_url": "https://example.com",
                "model": "deepseek-v3",
            }
        },
        project_config={"project_name": "Demo", "project_path": "./projects/demo"},
    )

    provider = service.get_active_provider_config()

    assert provider is not None
    assert provider["name"] == "eggfans"
    assert provider["api_key"] == "sk-live-value"
    assert provider["model"] == "deepseek-v3"


def test_save_runtime_config_keeps_existing_key_when_api_key_is_blank(tmp_path):
    service = ConfigService(db_path=tmp_path / "config.db")
    service.save_runtime_config(
        default_provider="eggfans",
        providers={
            "eggfans": {
                "api_key": "sk-existing-9999",
                "base_url": "https://example.com",
                "model": "m1",
            }
        },
        project_config={"project_name": "Demo", "project_path": "./projects/demo"},
    )

    service.save_runtime_config(
        default_provider="eggfans",
        providers={
            "eggfans": {
                "api_key": "",
                "base_url": "https://example.com/v2",
                "model": "m2",
                "has_api_key": True,
            }
        },
        project_config={"project_name": "Demo", "project_path": "./projects/demo"},
    )

    provider = service.get_active_provider_config()
    assert provider is not None
    assert provider["api_key"] == "sk-existing-9999"
    assert provider["base_url"] == "https://example.com/v2"
    assert provider["model"] == "m2"


def test_service_migrates_legacy_json_when_database_is_empty(tmp_path):
    legacy_json = tmp_path / "llm_providers.json"
    legacy_json.write_text(
        json.dumps(
            {
                "default_provider": "eggfans",
                "providers": {
                    "eggfans": {
                        "api_key": "sk-legacy",
                        "base_url": "https://example.com",
                        "model": "m1",
                        "enabled": True,
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    service = ConfigService(db_path=tmp_path / "config.db", legacy_json_path=legacy_json)
    provider = service.get_active_provider_config()

    assert provider is not None
    assert provider["api_key"] == "sk-legacy"
    assert service.get_runtime_config(mask_secrets=True)["default_provider"] == "eggfans"


def test_custom_db_path_does_not_auto_migrate_default_legacy_config(tmp_path):
    service = ConfigService(db_path=tmp_path / "config.db")

    assert service.get_active_provider_config() is None
    assert service.get_runtime_config(mask_secrets=False)["providers"] == {}


def test_save_runtime_config_can_explicitly_clear_api_key(tmp_path):
    service = ConfigService(db_path=tmp_path / "config.db")
    service.save_runtime_config(
        default_provider="eggfans",
        providers={
            "eggfans": {
                "api_key": "sk-existing-9999",
                "base_url": "https://example.com",
                "model": "m1",
            }
        },
        project_config={"project_name": "Demo", "project_path": "./projects/demo"},
    )

    service.save_runtime_config(
        default_provider="eggfans",
        providers={
            "eggfans": {
                "api_key": "",
                "clear_api_key": True,
                "base_url": "https://example.com",
                "model": "m1",
            }
        },
        project_config={"project_name": "Demo", "project_path": "./projects/demo"},
    )

    provider = service.get_provider_config("eggfans", mask_secrets=False)
    assert provider is not None
    assert provider["api_key"] == ""


def test_save_runtime_config_rolls_back_on_partial_failure(tmp_path, monkeypatch):
    service = ConfigService(db_path=tmp_path / "config.db")
    service.save_runtime_config(
        default_provider="eggfans",
        providers={
            "eggfans": {
                "api_key": "sk-old",
                "base_url": "https://old.example.com",
                "model": "m1",
            }
        },
        project_config={"project_name": "Old", "project_path": "./projects/old"},
    )

    monkeypatch.setattr(
        service,
        "_save_project_config",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    with pytest.raises(RuntimeError):
        service.save_runtime_config(
            default_provider="eggfans",
            providers={
                "eggfans": {
                    "api_key": "sk-new",
                    "base_url": "https://new.example.com",
                    "model": "m2",
                }
            },
            project_config={"project_name": "New", "project_path": "./projects/new"},
    )

    provider = service.get_active_provider_config()
    assert provider is not None
    assert provider["api_key"] == "sk-old"
    assert provider["base_url"] == "https://old.example.com"


@pytest.mark.asyncio
async def test_workflow_executor_returns_structured_error_when_no_active_provider(tmp_path):
    service = ConfigService(db_path=tmp_path / "config.db")
    executor = WritingWorkflowExecutor(config_service=service)

    result = await executor.execute_chapter_workflow(
        novel_id="n1",
        chapter_num=1,
        outline="test",
    )

    assert result["status"] == "error"
    assert "LLM" in result["message"] or "provider" in result["message"]
