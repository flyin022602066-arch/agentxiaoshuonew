import pytest


@pytest.mark.asyncio
async def test_agent_routes_delegate_to_agent_service(client, monkeypatch):
    from app.api import agent_routes

    class StubAgentService:
        def get_agents_status(self):
            return {"agents": [{"id": "editor"}], "total": 1, "timestamp": "now"}

    monkeypatch.setattr(agent_routes, "get_agent_service", lambda: StubAgentService())
    response = await client.get("/api/agents/status")
    body = response.json()
    assert body["success"] is True
    assert body["data"]["total"] == 1


@pytest.mark.asyncio
async def test_ai_routes_delegate_to_ai_service(client, monkeypatch):
    from app.api import ai_routes

    class StubAIService:
        def list_templates(self):
            return {"core": [{"id": "tpl-1"}]}

    monkeypatch.setattr(ai_routes, "get_ai_service", lambda: StubAIService())
    response = await client.get("/api/ai/templates")
    body = response.json()
    assert body["success"] is True
    assert body["data"]["core"][0]["id"] == "tpl-1"


@pytest.mark.asyncio
async def test_auto_routes_delegate_to_auto_service(client, monkeypatch):
    from app.api import auto_routes

    class StubAutoService:
        async def create_novel(self, data, task_id=None):
            return {"status": "success", "novel_id": "n-1", "blueprint": {}, "auto_style": data.get("auto_style", {}), "first_chapter": {}}

    class StubTaskManager:
        def create_task(self, task_id, task_type, metadata=None):
            return None

    captured = {}

    async def stub_execute(task_id, data):
        captured["task_id"] = task_id
        captured["title"] = data.get("title")

    monkeypatch.setattr(auto_routes, "get_auto_service", lambda: StubAutoService())
    monkeypatch.setattr(auto_routes, "get_task_manager", lambda: StubTaskManager())
    monkeypatch.setattr(auto_routes, "generate_task_id", lambda prefix: f"{prefix}_1")
    monkeypatch.setattr(auto_routes, "_execute_auto_creation", stub_execute)

    scheduled = []

    def fake_create_task(coro):
        scheduled.append(coro)
        return None

    monkeypatch.setattr(auto_routes.asyncio, "create_task", fake_create_task)

    response = await client.post("/api/auto/create", json={"title": "测试书"})
    body = response.json()
    assert body["success"] is True
    assert body["data"]["task_id"] == "auto_1"
    assert body["data"]["status"] == "pending"
    await scheduled[0]
    assert captured["title"] == "测试书"


@pytest.mark.asyncio
async def test_novel_routes_support_delete_chapter(client, monkeypatch):
    from app.api import novel_routes

    class StubChapterService:
        def delete_chapter(self, novel_id, chapter_num):
            return True

    class StubDB:
        def get_novel(self, novel_id):
            return {"id": novel_id}

    monkeypatch.setattr(novel_routes, "get_chapter_service", lambda: StubChapterService())
    monkeypatch.setattr("app.novel_db.get_novel_database", lambda: StubDB())

    response = await client.delete("/api/novels/n-1/chapters/2")
    body = response.json()

    assert response.status_code == 200
    assert body["success"] is True


def test_auto_creation_system_resolves_author_style():
    from app.novel_architect import AutoCreationSystem

    system = AutoCreationSystem({"api_key": "x", "base_url": "https://example.com", "model": "test", "timeout": 60})
    style = system._resolve_author_style({"mode": "manual", "style_id": "wuxia_gulong"})

    assert style["style_id"] == "wuxia_gulong"
    assert style["name"] == "古龙派"


def test_author_style_templates_include_expanded_builtin_styles():
    from app.author_styles import get_author_style, list_author_styles

    styles = list_author_styles()
    style_ids = {style["style_id"] for style in styles}

    assert "wuxia_liangyusheng" in style_ids
    assert "wuxia_wenruian" in style_ids
    assert "literary_zhangailing" in style_ids
    assert "realism_moyan" in style_ids
    assert "web_heianhuolong" in style_ids
    assert "web_chendong" in style_ids
    assert "web_tiancantudou" in style_ids
    assert "web_wochi_xihongshi" in style_ids
    assert "web_ergen" in style_ids
    assert "web_tangjia_sanshao" in style_ids
    assert get_author_style("wuxia_jinyong")["guidelines"]


def test_author_style_strength_and_forbidden_rules_are_available():
    from app.author_styles import apply_style_strength, get_author_style

    style = apply_style_strength(get_author_style("wuxia_gulong"), "strong")

    assert style["strength"] == "strong"
    assert style["forbidden"]
    assert "强风格化" in style["strength_instruction"]


@pytest.mark.asyncio
async def test_ai_style_preview_route_delegates_to_service(client, monkeypatch):
    from app.api import ai_routes

    class StubAIService:
        async def generate_style_preview(self, data):
            return {"style_id": data.get("style_id"), "preview": "测试文本"}

    monkeypatch.setattr(ai_routes, "get_ai_service", lambda: StubAIService())
    response = await client.post("/api/ai/generate-style-preview", json={"style_id": "web_heianhuolong", "strength": "medium"})
    body = response.json()

    assert response.status_code == 200
    assert body["success"] is True
    assert body["data"]["style_id"] == "web_heianhuolong"


@pytest.mark.asyncio
async def test_school_routes_delegate_to_school_service(client, monkeypatch):
    from app.api import school_routes

    class StubSchoolService:
        def list_schools(self, category=None):
            return {"schools": [{"id": "s1"}], "total": 1}

    monkeypatch.setattr(school_routes, "get_school_service", lambda: StubSchoolService())
    response = await client.get("/api/schools")
    body = response.json()
    assert body["success"] is True
    assert body["data"]["schools"][0]["id"] == "s1"
