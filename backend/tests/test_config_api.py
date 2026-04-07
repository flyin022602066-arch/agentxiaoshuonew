from app.services.config_service import ConfigService


def _seed_runtime_config(service: ConfigService):
    service.save_runtime_config(
        default_provider="eggfans",
        providers={
            "eggfans": {
                "api_key": "sk-seeded-1234",
                "base_url": "https://example.com",
                "model": "deepseek-v3",
                "enabled": True,
            }
        },
        project_config={"project_name": "Demo", "project_path": "./projects/demo"},
    )


import pytest


@pytest.mark.asyncio
async def test_get_config_api_never_returns_plaintext_api_key(client, tmp_path, monkeypatch):
    from app.api import config_routes

    service = ConfigService(db_path=tmp_path / "config.db")
    _seed_runtime_config(service)
    monkeypatch.setattr(config_routes, "get_config_service", lambda: service)

    response = await client.get("/api/config")
    body = response.json()

    assert response.status_code == 200
    assert body["data"]["providers"]["eggfans"]["api_key"] == ""
    assert body["data"]["providers"]["eggfans"]["has_api_key"] is True
    assert "sk-" not in str(body)


@pytest.mark.asyncio
async def test_get_config_api_returns_mask_metadata_for_frontend(client, tmp_path, monkeypatch):
    from app.api import config_routes

    service = ConfigService(db_path=tmp_path / "config.db")
    _seed_runtime_config(service)
    monkeypatch.setattr(config_routes, "get_config_service", lambda: service)

    body = (await client.get("/api/config")).json()
    provider = body["data"]["providers"]["eggfans"]

    assert "has_api_key" in provider
    assert "masked_api_key" in provider
    assert provider["api_key"] == ""


@pytest.mark.asyncio
async def test_llm_test_endpoint_returns_structured_config_error_when_provider_is_invalid(client, tmp_path, monkeypatch):
    from app.api import config_routes

    service = ConfigService(db_path=tmp_path / "config.db")
    monkeypatch.setattr(config_routes, "get_config_service", lambda: service)

    response = await client.post("/api/llm/test", json={"provider": "eggfans"})
    body = response.json()

    assert response.status_code in (200, 400, 422)
    assert body["status"] == "error"
    assert body["error"]["message"]
    assert "sk-" not in str(body)


@pytest.mark.asyncio
async def test_health_reports_ready_when_active_provider_exists(client, tmp_path, monkeypatch):
    from app.api import health

    service = ConfigService(db_path=tmp_path / "config.db")
    _seed_runtime_config(service)
    monkeypatch.setattr(health, "get_config_service", lambda: service)

    body = (await client.get("/api/health")).json()
    llm_checks = body["checks"]["llm_providers"]

    assert any(item.get("status") == "ok" for item in llm_checks)


@pytest.mark.asyncio
async def test_health_reports_config_error_when_active_provider_missing(client, tmp_path, monkeypatch):
    from app.api import health

    service = ConfigService(db_path=tmp_path / "config.db")
    monkeypatch.setattr(health, "get_config_service", lambda: service)

    body = (await client.get("/api/health")).json()
    llm_checks = body["checks"]["llm_providers"]

    assert body["status"] in ("degraded", "unhealthy")
    assert any(item.get("status") in ("warning", "error") for item in llm_checks)


@pytest.mark.asyncio
async def test_health_response_never_leaks_plaintext_api_keys(client, tmp_path, monkeypatch):
    from app.api import health

    service = ConfigService(db_path=tmp_path / "config.db")
    _seed_runtime_config(service)
    monkeypatch.setattr(health, "get_config_service", lambda: service)

    body = (await client.get("/api/health")).json()

    assert "sk-" not in str(body)


@pytest.mark.asyncio
async def test_check_redis_handles_non_awaitable_close_result(monkeypatch):
    from app.api import health

    class StubRedisClient:
        def ping(self):
            return True

        def close(self):
            return False

    class StubRedisModule:
        @staticmethod
        def from_url(url, socket_timeout=5):
            return StubRedisClient()

    class StubAppConfig:
        redis_url = "redis://example.test:6379/0"

    class StubConfig:
        app_config = StubAppConfig()

    monkeypatch.setattr("redis.asyncio", StubRedisModule(), raising=False)
    monkeypatch.setattr("app.config.get_config_manager", lambda: StubConfig())

    result = await health.check_redis()

    assert result["status"] == "ok"
    assert result["url"] == "redis://example.test:6379/0"
