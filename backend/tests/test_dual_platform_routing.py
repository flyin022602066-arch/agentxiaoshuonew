import pytest

from app.services.style_learner import StyleLearner


@pytest.mark.asyncio
async def test_explicit_fanqiao_platform_is_passed_to_workflow(monkeypatch):
    from app.services.writing_service import WritingService

    service = WritingService()
    service.style_learner = StyleLearner()
    captured = {}

    class StubDB:
        def get_novel(self, novel_id):
            return {"settings": {}}
        def get_characters(self, novel_id):
            return []
        def update_novel(self, novel_id, settings=None):
            return None

    class StubChapterService:
        def save_chapter(self, **kwargs):
            return None

    class StubExecutor:
        llm_client = {"api_key": "k"}
        async def execute_chapter_workflow(self, **kwargs):
            captured.update(kwargs)
            return {
                "status": "success",
                "content": "章节内容" * 120,
                "word_count": 1200,
                "workflow_id": "wf-fanqiao",
            }

    monkeypatch.setattr(service, "db", StubDB())
    monkeypatch.setattr(service, "chapter_service", StubChapterService())
    monkeypatch.setattr("app.services.writing_service.get_workflow_executor", lambda: StubExecutor())

    result = await service.create_chapter_workflow({
        "novel_id": "n1",
        "chapter_num": 1,
        "outline": "主角夜探废楼。",
        "platform": "fanqiao",
    })

    assert result["status"] == "success"
    assert captured["style"] == "fanqiao"


@pytest.mark.asyncio
async def test_explicit_qimao_platform_is_passed_to_workflow(monkeypatch):
    from app.services.writing_service import WritingService

    service = WritingService()
    service.style_learner = StyleLearner()
    captured = {}

    class StubDB:
        def get_novel(self, novel_id):
            return {"settings": {}}
        def get_characters(self, novel_id):
            return []
        def update_novel(self, novel_id, settings=None):
            return None

    class StubChapterService:
        def save_chapter(self, **kwargs):
            return None

    class StubExecutor:
        llm_client = {"api_key": "k"}
        async def execute_chapter_workflow(self, **kwargs):
            captured.update(kwargs)
            return {
                "status": "success",
                "content": "章节内容" * 120,
                "word_count": 1200,
                "workflow_id": "wf-qimao",
            }

    monkeypatch.setattr(service, "db", StubDB())
    monkeypatch.setattr(service, "chapter_service", StubChapterService())
    monkeypatch.setattr("app.services.writing_service.get_workflow_executor", lambda: StubExecutor())

    result = await service.create_chapter_workflow({
        "novel_id": "n1",
        "chapter_num": 1,
        "outline": "她深夜回到旧宅。",
        "platform": "qimao",
    })

    assert result["status"] == "success"
    assert captured["style"] == "qimao"


@pytest.mark.asyncio
async def test_auto_recommends_fanqiao_when_platform_unspecified(monkeypatch):
    from app.services.writing_service import WritingService

    service = WritingService()
    service.style_learner = StyleLearner()
    captured = {}

    class StubDB:
        def get_novel(self, novel_id):
            return {"settings": {}}
        def get_characters(self, novel_id):
            return []
        def update_novel(self, novel_id, settings=None):
            return None

    class StubChapterService:
        def save_chapter(self, **kwargs):
            return None

    class StubExecutor:
        llm_client = {"api_key": "k"}
        async def execute_chapter_workflow(self, **kwargs):
            captured.update(kwargs)
            return {
                "status": "success",
                "content": "章节内容" * 120,
                "word_count": 1200,
                "workflow_id": "wf-auto-fanqiao",
            }

    monkeypatch.setattr(service, "db", StubDB())
    monkeypatch.setattr(service, "chapter_service", StubChapterService())
    monkeypatch.setattr(service.style_learner, "match_platform", lambda text: "fanqiao")
    monkeypatch.setattr("app.services.writing_service.get_workflow_executor", lambda: StubExecutor())

    result = await service.create_chapter_workflow({
        "novel_id": "n1",
        "chapter_num": 1,
        "outline": "主角刚进门，追兵就已经贴了上来。",
    })

    assert result["status"] == "success"
    assert captured["style"] == "fanqiao"


@pytest.mark.asyncio
async def test_auto_recommends_qimao_when_platform_unspecified(monkeypatch):
    from app.services.writing_service import WritingService

    service = WritingService()
    captured = {}

    class StubDB:
        def get_novel(self, novel_id):
            return {"settings": {}}
        def get_characters(self, novel_id):
            return []
        def update_novel(self, novel_id, settings=None):
            return None

    class StubChapterService:
        def save_chapter(self, **kwargs):
            return None

    class StubExecutor:
        llm_client = {"api_key": "k"}
        async def execute_chapter_workflow(self, **kwargs):
            captured.update(kwargs)
            return {
                "status": "success",
                "content": "章节内容" * 120,
                "word_count": 1200,
                "workflow_id": "wf-auto-qimao",
            }

    monkeypatch.setattr(service, "db", StubDB())
    monkeypatch.setattr(service, "chapter_service", StubChapterService())
    monkeypatch.setattr(service.style_learner, "match_platform", lambda text: "qimao")
    monkeypatch.setattr("app.services.writing_service.get_workflow_executor", lambda: StubExecutor())

    result = await service.create_chapter_workflow({
        "novel_id": "n1",
        "chapter_num": 1,
        "outline": "她深夜回屋，旧人把茶盏轻轻推到她手边。",
    })

    assert result["status"] == "success"
    assert captured["style"] == "qimao"


@pytest.mark.asyncio
async def test_platform_metadata_is_exposed_in_results(monkeypatch):
    from app.services.writing_service import WritingService

    service = WritingService()

    class StubDB:
        def get_novel(self, novel_id):
            return {"settings": {}}
        def get_characters(self, novel_id):
            return []
        def update_novel(self, novel_id, settings=None):
            return None

    class StubChapterService:
        def save_chapter(self, **kwargs):
            return None

    class StubExecutor:
        llm_client = {"api_key": "k"}
        async def execute_chapter_workflow(self, **kwargs):
            return {
                "status": "success",
                "content": "章节内容" * 120,
                "word_count": 1200,
                "workflow_id": "wf-meta",
            }

    monkeypatch.setattr(service, "db", StubDB())
    monkeypatch.setattr(service, "chapter_service", StubChapterService())
    monkeypatch.setattr(service.style_learner, "match_platform", lambda text: "fanqiao")
    monkeypatch.setattr("app.services.writing_service.get_workflow_executor", lambda: StubExecutor())

    result = await service.create_chapter_workflow({
        "novel_id": "n1",
        "chapter_num": 1,
        "outline": "主角刚进门，追兵就已经贴了上来。",
    })

    assert result["status"] == "success"
    assert result["platform"] == "fanqiao"
    assert result["platform_resolution"] == "auto_recommended"


@pytest.mark.asyncio
async def test_platform_routing_enters_expected_adaptation_branch(monkeypatch):
    from app.workflow_executor import WritingWorkflowExecutor

    async def _run(style_value: str):
        executor = WritingWorkflowExecutor()
        executor.llm_client = {"api_key": "k", "base_url": "https://example.com", "model": "demo", "timeout": 60}
        branch = {"fanqie": False, "qimao": False}

        async def stub_prev(*args, **kwargs):
            return []

        async def stub_refine(*args, **kwargs):
            return "细化大纲"

        async def stub_prepare(*args, **kwargs):
            return {"character_notes": "角色设定", "character_state_packet": {}}

        async def stub_write(*args, **kwargs):
            return ("章节内容" * 200)

        async def stub_polish(content, style="default", style_strength=None):
            return content

        async def stub_consistency(*args, **kwargs):
            return {
                "issues": [],
                "has_issues": False,
                "quality_score": 90,
                "word_count": 1800,
                "style_feedback": {"style_id": style_value, "score": 80, "matched_features": [], "missing_features": [], "summary": "ok"},
                "review_packet": {"fatal_issues": [], "important_issues": [], "optional_issues": [], "scores": {"continuity": 85, "plot_progress": 80, "character_consistency": 82, "style_match": 80, "ending_strength": 75, "naturalness": 80}, "style_feedback": {}, "pass_to_editor": False},
            }

        async def stub_final(content, check_result, style="default", style_strength=None):
            return content

        async def stub_fanqie(content, diagnostics):
            branch["fanqie"] = True
            return content

        async def stub_qimao(content, diagnostics):
            branch["qimao"] = True
            return content

        monkeypatch.setattr(executor, "_get_previous_chapters", stub_prev)
        monkeypatch.setattr(executor, "_refine_outline_smart", stub_refine)
        monkeypatch.setattr(executor, "_prepare_characters_smart", stub_prepare)
        monkeypatch.setattr(executor, "_write_draft_smart", stub_write)
        monkeypatch.setattr(executor, "_polish_dialogue", stub_polish)
        monkeypatch.setattr(executor, "_consistency_check_smart", stub_consistency)
        monkeypatch.setattr(executor, "_final_review", stub_final)
        monkeypatch.setattr(executor, "_fanqie_adaptation_polish", stub_fanqie)
        monkeypatch.setattr(executor, "_qimao_adaptation_polish", stub_qimao)

        result = await executor.execute_chapter_workflow(
            novel_id="novel-route",
            chapter_num=1,
            outline="测试路由分支。",
            word_count_target=1800,
            style=style_value,
        )

        return result, branch

    _, fanqie_branch = await _run("fanqiao")
    _, qimao_branch = await _run("qimao")

    assert fanqie_branch["fanqie"] is True
    assert fanqie_branch["qimao"] is False
    assert qimao_branch["qimao"] is True
    assert qimao_branch["fanqie"] is False
