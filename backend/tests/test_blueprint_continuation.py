import pytest


@pytest.mark.asyncio
async def test_auto_creation_persists_blueprint_into_novel_settings(monkeypatch, tmp_path):
    from app import novel_architect as novel_architect_module
    from app.novel_architect import AutoCreationSystem
    from app.novel_db import NovelDatabase

    db = NovelDatabase(str(tmp_path / "novels.db"))
    monkeypatch.setattr("app.novel_db.get_novel_database", lambda: db)

    blueprint = {
        "world_map": {"world_name": "九州"},
        "macro_plot": {"volumes": [{"volume_num": 1, "main_goal": "崛起"}]},
        "character_system": {"protagonist": {"name": "林川", "goal": "登顶"}},
        "hook_network": {"short_term": [{"description": "黑石来历", "reveal_chapter": 5}]},
    }

    class StubArchitect:
        async def create_novel_blueprint(self, title, genre, description, chapter_count):
            return blueprint

    system = AutoCreationSystem({"api_key": "k", "base_url": "https://example.com", "model": "demo", "timeout": 30})
    system.architect = StubArchitect()

    async def stub_generate_first_chapter(novel_id, bp, auto_style=None, progress_callback=None):
        db.create_chapter(novel_id, 1, "第一章", "主角登场")
        db.update_chapter(novel_id, 1, content="第一章正文内容足够长，用于验证自动创作链路的持久化。", title="第一章", outline="主角登场", status="published")
        return {"status": "success", "content": "第一章正文内容足够长，用于验证自动创作链路的持久化。", "word_count": 29}

    system._generate_first_chapter = stub_generate_first_chapter

    result = await system.create_novel_from_scratch("测试书", "玄幻", "简介", 1200, {"style_id": "default", "strength": "medium"})
    novel = db.get_novel(result["novel_id"])

    assert result["status"] == "success"
    assert novel is not None
    assert novel["settings"]["blueprint"]["world_map"]["world_name"] == "九州"
    assert novel["settings"]["macro_plot"]["volumes"][0]["main_goal"] == "崛起"
    assert novel["settings"]["character_system"]["protagonist"]["name"] == "林川"
    assert novel["settings"]["hook_network"]["short_term"][0]["description"] == "黑石来历"


@pytest.mark.asyncio
async def test_writing_service_passes_blueprint_context_to_executor(monkeypatch, tmp_path):
    from app.services.writing_service import WritingService
    from app.novel_db import NovelDatabase

    db = NovelDatabase(str(tmp_path / "novels.db"))
    novel_id = db.create_novel(
        "续写测试",
        "玄幻",
        "简介",
        settings={
            "world_map": {"world_name": "九州"},
            "macro_plot": {"volumes": [{"volume_num": 1, "main_goal": "崛起"}]},
            "character_system": {"protagonist": {"name": "林川", "goal": "登顶"}},
            "hook_network": {"short_term": [{"description": "黑石来历", "reveal_chapter": 5}]},
            "active_style": {"style_id": "default", "strength": "medium"},
        },
    )
    db.create_chapter(novel_id, 1, "第一章", "主角登场")
    db.update_chapter(novel_id, 1, content="前文正文内容", title="第一章", outline="主角登场", status="published")

    captured = {}

    class StubExecutor:
        llm_client = {"api_key": "k"}

        async def execute_chapter_workflow(self, **kwargs):
            captured.update(kwargs)
            return {"status": "success", "content": "第二章正文内容足够长用于测试。" * 10, "word_count": 150}

    class StubChapterService:
        def save_chapter(self, **kwargs):
            captured["saved"] = kwargs
            return kwargs

    monkeypatch.setattr("app.services.writing_service.get_novel_database", lambda: db)
    monkeypatch.setattr("app.services.writing_service.get_workflow_executor", lambda: StubExecutor())
    monkeypatch.setattr("app.services.writing_service.get_chapter_service", lambda: StubChapterService())

    service = WritingService()
    result = await service.create_chapter_workflow({
        "novel_id": novel_id,
        "chapter_num": 2,
        "outline": "承接前文推进主线",
        "word_count_target": 3000,
        "style": "default",
        "style_context": {"style_id": "default", "strength": "medium"},
    })

    assert result["status"] == "success"
    assert captured["world_map"]["world_name"] == "九州"
    assert captured["macro_plot"]["volumes"][0]["main_goal"] == "崛起"
    assert captured["protagonist_halo"]["name"] == "林川"
    assert "黑石来历" in captured["outline"]
    assert "林川" in captured["outline"]
    assert captured["saved"]["chapter_num"] == 2
