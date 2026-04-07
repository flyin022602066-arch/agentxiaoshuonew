import pytest


def test_get_workflow_executor_initializes_agents_when_registry_empty(monkeypatch):
    import app.workflow_executor as workflow_module
    from app.agents.registry import registry

    registry.clear()
    workflow_module._workflow_executor = None

    created = {"called": False}

    def stub_create_agents(config):
        created["called"] = True

    monkeypatch.setattr(workflow_module, "create_agents", stub_create_agents)

    executor = workflow_module.get_workflow_executor()

    assert executor is not None
    assert created["called"] is True


@pytest.mark.asyncio
async def test_execute_chapter_workflow_falls_back_when_final_review_times_out(monkeypatch):
    from app.workflow_executor import WritingWorkflowExecutor

    executor = WritingWorkflowExecutor()
    executor.llm_client = {"api_key": "k", "base_url": "https://example.com", "model": "demo", "timeout": 60}

    async def stub_prev_chapters(novel_id, current_chapter, count=3):
        return [{"chapter_num": 1, "content": "第一章正文" * 200}]

    async def stub_refine(*args, **kwargs):
        return "第二章细化大纲"

    async def stub_prepare(*args, **kwargs):
        return "角色准备"

    async def stub_write(*args, **kwargs):
        return "第二章正文" * 300

    async def stub_polish(content, style="default"):
        return content + "。"

    async def stub_check(*args, **kwargs):
        return {
            "issues": ["需要润色个别句子"],
            "has_issues": True,
            "quality_score": 87,
            "word_count": 1200,
        }

    async def stub_final_review(content, check_result):
        raise Exception("LLM 读取超时重试 3 次失败：ReadTimeout")

    monkeypatch.setattr(executor, "_get_previous_chapters", stub_prev_chapters)
    monkeypatch.setattr(executor, "_refine_outline_smart", stub_refine)
    monkeypatch.setattr(executor, "_prepare_characters_smart", stub_prepare)
    monkeypatch.setattr(executor, "_write_draft_smart", stub_write)
    monkeypatch.setattr(executor, "_polish_dialogue", stub_polish)
    monkeypatch.setattr(executor, "_consistency_check_smart", stub_check)
    monkeypatch.setattr(executor, "_final_review", stub_final_review)

    result = await executor.execute_chapter_workflow(
        novel_id="novel-timeout",
        chapter_num=2,
        outline="第二章大纲",
        word_count_target=2200,
        style="default",
    )

    assert result["status"] == "success"
    assert result["content"].startswith("第二章正文")
    assert result["word_count"] >= 1000


@pytest.mark.asyncio
async def test_execute_chapter_workflow_falls_back_when_character_step_times_out(monkeypatch):
    from app.workflow_executor import WritingWorkflowExecutor

    executor = WritingWorkflowExecutor()
    executor.llm_client = {"api_key": "k", "base_url": "https://example.com", "model": "demo", "timeout": 60}

    async def stub_prev_chapters(novel_id, current_chapter, count=3):
        return [{"chapter_num": 1, "content": "第一章正文" * 100}]

    async def stub_refine(*args, **kwargs):
        return "第二章细化大纲"

    async def stub_prepare(*args, **kwargs):
        raise TimeoutError("character step timeout")

    async def stub_write(*args, **kwargs):
        return "第二章正文" * 260

    async def stub_polish(content, style="default"):
        return content

    async def stub_check(*args, **kwargs):
        return {
            "issues": [],
            "has_issues": False,
            "quality_score": 90,
            "word_count": len(args[0]) if args else 1200,
            "style_feedback": {"style_id": "default", "score": 70, "matched_features": [], "missing_features": [], "summary": ""},
            "review_packet": {"fatal_issues": [], "important_issues": [], "optional_issues": [], "scores": {}, "style_feedback": {}, "pass_to_editor": False},
        }

    async def stub_final(content, check_result, style="default", style_strength=None):
        return content

    monkeypatch.setattr(executor, "_get_previous_chapters", stub_prev_chapters)
    monkeypatch.setattr(executor, "_refine_outline_smart", stub_refine)
    monkeypatch.setattr(executor, "_prepare_characters_smart", stub_prepare)
    monkeypatch.setattr(executor, "_write_draft_smart", stub_write)
    monkeypatch.setattr(executor, "_polish_dialogue", stub_polish)
    monkeypatch.setattr(executor, "_consistency_check_smart", stub_check)
    monkeypatch.setattr(executor, "_final_review", stub_final)

    result = await executor.execute_chapter_workflow(
        novel_id="novel-timeout-step2",
        chapter_num=2,
        outline="第二章大纲",
        word_count_target=2200,
        style="default",
    )

    assert result["status"] == "success"
    assert result["character_state_packet"]["protagonist"]["name"]
