import pytest


@pytest.mark.asyncio
async def test_auto_create_endpoint_submits_background_task(client, monkeypatch, tmp_path):
    from app import novel_architect as novel_architect_module
    from app.novel_db import NovelDatabase
    from app.api import auto_routes

    db = NovelDatabase(str(tmp_path / "novels.db"))

    class StubAutoCreationSystem:
        llm_client = {"api_key": "k", "base_url": "https://example.com", "model": "demo"}

        async def create_novel_from_scratch(self, title, genre, description, chapter_count, auto_style, progress_callback=None):
            novel_id = db.create_novel(
                title,
                genre,
                description,
                settings={"auto_style": auto_style, "active_style": auto_style},
            )
            db.create_chapter(novel_id, 1, "第一章", "主角登场")
            db.update_chapter(novel_id, 1, content="这是完整第一章正文，用于验证一键创作链路。", title="第一章", outline="主角登场", status="published")

            return {
                "status": "success",
                "novel_id": novel_id,
                "blueprint": {
                    "world_map": {"world_name": "测试世界"},
                    "macro_plot": {"total_chapters": chapter_count},
                },
                "first_chapter": {
                    "status": "success",
                    "chapter_num": 1,
                    "content": "这是完整第一章正文，用于验证一键创作链路。",
                    "word_count": len("这是完整第一章正文，用于验证一键创作链路。"),
                },
            }

    monkeypatch.setattr(novel_architect_module, "get_auto_creation_system", lambda: StubAutoCreationSystem())

    created = {}

    class StubTaskManager:
        def create_task(self, task_id, task_type, metadata=None):
            created.update({"task_id": task_id, "task_type": task_type, "metadata": metadata or {}})

    async def stub_execute(task_id, data):
        created["scheduled"] = {"task_id": task_id, "title": data["title"]}

    monkeypatch.setattr(auto_routes, "get_task_manager", lambda: StubTaskManager())
    monkeypatch.setattr(auto_routes, "generate_task_id", lambda prefix: f"{prefix}_123")
    monkeypatch.setattr(auto_routes, "_execute_auto_creation", stub_execute)

    scheduled = []

    def fake_create_task(coro):
        scheduled.append(coro)
        return None

    monkeypatch.setattr(auto_routes.asyncio, "create_task", fake_create_task)

    response = await client.post(
        "/api/auto/create",
        json={
            "title": "一键创作测试",
            "genre": "玄幻",
            "description": "测试简介",
            "chapter_count": 3000,
            "auto_style": {"style_id": "default", "strength": "medium"},
        },
    )
    body = response.json()

    assert response.status_code == 200
    assert body["status"] == "success"
    assert body["data"]["task_id"] == "auto_123"
    assert body["data"]["status"] == "pending"
    assert created["task_type"] == "auto_creation"
    assert created["metadata"]["title"] == "一键创作测试"
    assert scheduled

    await scheduled[0]
    assert created["scheduled"]["title"] == "一键创作测试"


@pytest.mark.asyncio
async def test_auto_service_passes_style_and_chapter_count_to_creation_system(monkeypatch):
    from app.services.auto_service import AutoService
    from app import novel_architect as novel_architect_module
    from app.services import auto_service as auto_service_module

    captured = {}

    class StubAutoCreationSystem:
        async def create_novel_from_scratch(self, title, genre, description, chapter_count, auto_style, progress_callback=None):
            captured.update({
                "title": title,
                "genre": genre,
                "description": description,
                "chapter_count": chapter_count,
                "auto_style": auto_style,
            })
            return {"status": "success", "novel_id": "n1", "blueprint": {}, "first_chapter": {"content": "正文"}}

    monkeypatch.setattr(novel_architect_module, "get_auto_creation_system", lambda: StubAutoCreationSystem())

    updates = []

    class StubTaskManager:
        def update_task(self, task_id, status=None, progress=None, current_stage=None):
            updates.append({"task_id": task_id, "progress": progress, "current_stage": current_stage})

    monkeypatch.setattr("app.tasks.task_manager.get_task_manager", lambda: StubTaskManager())

    service = AutoService()
    result = await service.create_novel({
        "title": "风格测试",
        "genre": "都市",
        "description": "简介",
        "chapter_count": 1200,
        "auto_style": {"style_id": "wuxia_jinyong", "strength": "strong"},
    }, task_id="auto_1")

    assert result["status"] == "success"
    assert captured == {
        "title": "风格测试",
        "genre": "都市",
        "description": "简介",
        "chapter_count": 1200,
        "auto_style": {"style_id": "wuxia_jinyong", "strength": "strong"},
    }
    assert updates[0]["task_id"] == "auto_1"


@pytest.mark.asyncio
async def test_auto_creation_first_chapter_allows_lower_style_score(monkeypatch, tmp_path):
    from app.novel_architect import AutoCreationSystem
    from app.novel_db import NovelDatabase

    db = NovelDatabase(str(tmp_path / "novels.db"))
    monkeypatch.setattr("app.novel_db.get_novel_database", lambda: db)

    captured = {}

    class StubExecutor:
        async def execute_chapter_workflow(self, **kwargs):
            captured.update(kwargs)
            return {
                "status": "success",
                "workflow_id": "wf_test",
                "content": "这是通过自动创作首章验证的正文。" * 80,
                "word_count": 2200,
                "outline_summary": "主角登场并触发初始冲突",
                "style_feedback": {
                    "style_id": "default",
                    "score": 43,
                    "matched_features": ["叙事清晰"],
                    "missing_features": ["风格稳定", "语感强化"],
                    "summary": "风格命中偏弱但仍可作为首章基线。",
                },
            }

    monkeypatch.setattr("app.workflow_executor.get_workflow_executor", lambda: StubExecutor())

    system = AutoCreationSystem(llm_client={"api_key": "k", "base_url": "https://example.com", "model": "demo"})
    blueprint = {
        "novel_info": {"title": "测试自动创作", "genre": "玄幻", "description": "简介"},
        "world_map": {"world_name": "测试世界", "power_system": {"name": "灵力体系"}},
        "character_system": {
            "protagonist": {"name": "林川", "goal": "活下去", "background": "山村少年"}
        },
        "macro_plot": {"total_chapters": 3000},
        "hook_network": {},
    }

    result = await system._generate_first_chapter(
        novel_id="novel_test",
        blueprint=blueprint,
        auto_style={"style_id": "default", "strength": "medium"},
    )

    assert result["status"] == "success"
    assert result["style_feedback"]["score"] == 43
    assert captured["min_style_score"] == 40
