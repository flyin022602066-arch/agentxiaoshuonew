import pytest


@pytest.mark.asyncio
async def test_workflow_falls_back_to_draft_when_dialogue_polish_fails(monkeypatch):
    from app.workflow_executor import WritingWorkflowExecutor

    executor = WritingWorkflowExecutor()
    executor.llm_client = {"api_key": "k", "base_url": "https://example.com", "model": "demo", "timeout": 60, "endpoint": "/v1/chat/completions"}

    async def stub_prev_chapters(novel_id, chapter_num):
        return []

    async def stub_refine(*args, **kwargs):
        return "细化大纲"

    async def stub_prepare(*args, **kwargs):
        return "角色设定"

    async def stub_write(*args, **kwargs):
        return "正文内容" * 400

    async def stub_polish(*args, **kwargs):
        raise RuntimeError("对话专家异常")

    async def stub_check(content, *args, **kwargs):
        return {"issues": "无问题", "has_issues": False, "quality_score": 82}

    async def stub_final(content, check_result):
        return content

    monkeypatch.setattr(executor, "_get_previous_chapters", stub_prev_chapters)
    monkeypatch.setattr(executor, "_refine_outline_smart", stub_refine)
    monkeypatch.setattr(executor, "_prepare_characters_smart", stub_prepare)
    monkeypatch.setattr(executor, "_write_draft_smart", stub_write)
    monkeypatch.setattr(executor, "_polish_dialogue", stub_polish)
    monkeypatch.setattr(executor, "_consistency_check_smart", stub_check)
    monkeypatch.setattr(executor, "_final_review", stub_final)

    result = await executor.execute_chapter_workflow(
        novel_id="novel_x",
        chapter_num=1,
        outline="测试大纲",
        word_count_target=2200,
        style="default",
    )

    assert result["status"] == "success"
    assert result["content"].startswith("正文内容")
    assert result["word_count"] >= 1000


@pytest.mark.asyncio
async def test_dialogue_polish_splits_long_content_into_segments(monkeypatch):
    from app.workflow_executor import WritingWorkflowExecutor

    executor = WritingWorkflowExecutor()
    executor.llm_client = {"api_key": "k", "base_url": "https://example.com", "model": "demo", "timeout": 60, "endpoint": "/v1/chat/completions"}

    calls = []

    async def stub_call(prompt: str, max_tokens: int = 2000):
        calls.append({"prompt": prompt, "max_tokens": max_tokens})
        segment = prompt.split("【原始片段】\n", 1)[1].strip()
        return segment

    monkeypatch.setattr(executor, "_call_llm", stub_call)

    content = "\n\n".join([f"第{i}段 对话与叙述内容。" * 80 for i in range(1, 7)])
    result = await executor._polish_dialogue(content, style="default")

    assert result
    assert len(calls) >= 2
    # max_tokens should be reasonable for Chinese text (not capped at 1800 anymore)
    assert all(call["max_tokens"] <= 4000 for call in calls)
    assert all(call["max_tokens"] >= 900 for call in calls)
