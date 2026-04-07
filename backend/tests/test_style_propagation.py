import pytest


@pytest.mark.asyncio
async def test_writing_prompt_includes_character_state_and_voice_constraints(monkeypatch):
    from app.workflow_executor import WritingWorkflowExecutor

    executor = WritingWorkflowExecutor()
    executor.llm_client = {"api_key": "k", "base_url": "https://example.com", "model": "demo", "timeout": 60}

    captured = {}

    async def stub_call_llm(prompt, max_tokens=2000):
        captured["prompt"] = prompt
        return "章节正文" * 300

    monkeypatch.setattr(executor, "_call_llm", stub_call_llm)

    result = await executor._write_draft(
        outline="主角夜探古寺，试探僧人来历。",
        character_notes=(
            "主角：林川\n"
            "当前目标：查清古寺里的密会。\n"
            "当前情绪：警惕克制。\n"
            "行为约束：不得轻易暴露身份，不得突然轻浮张扬。\n"
            "对白口吻：短句、压低情绪、不轻易解释。"
        ),
        word_count_target=2200,
        style="wuxia_gulong",
    )

    assert result
    assert "当前目标" in captured["prompt"]
    assert "当前情绪" in captured["prompt"]
    assert "行为约束" in captured["prompt"]
    assert "对白口吻" in captured["prompt"]


@pytest.mark.asyncio
async def test_refine_outline_includes_author_style_profile(monkeypatch):
    from app.workflow_executor import WritingWorkflowExecutor

    executor = WritingWorkflowExecutor()
    executor.llm_client = {"api_key": "k", "base_url": "https://example.com", "model": "demo", "timeout": 60}

    captured = {}

    async def stub_call_llm(prompt, max_tokens=2000):
        captured["prompt"] = prompt
        return "细化大纲"

    monkeypatch.setattr(executor, "_call_llm", stub_call_llm)

    result = await executor._refine_outline("主角夜探古寺", "wuxia_gulong", style_strength="strong")

    assert result == "细化大纲"
    assert "古龙派" in captured["prompt"]
    assert "强风格化" in captured["prompt"]
    assert "避免长篇背景讲解" in captured["prompt"]


@pytest.mark.asyncio
async def test_dialogue_polish_uses_detailed_style_rules(monkeypatch):
    from app.workflow_executor import WritingWorkflowExecutor

    executor = WritingWorkflowExecutor()
    executor.llm_client = {"api_key": "k", "base_url": "https://example.com", "model": "demo", "timeout": 60}

    prompts = []

    async def stub_call_llm(prompt, max_tokens=2000):
        prompts.append(prompt)
        return (("甲低声道：\"风不对。\"\n乙眯起眼，没有立刻回答。\n\n") * 60).strip()

    monkeypatch.setattr(executor, "_call_llm", stub_call_llm)

    content = ("甲说道：\"前面有动静。\"\n乙说道：\"小心。\"\n\n" * 60).strip()
    result = await executor._polish_dialogue(content, style="wuxia_jinyong", style_strength="strong")

    assert result
    assert prompts
    assert "金庸派" in prompts[0]
    assert "对白应体现身份、教养与门派气质" in prompts[0]
    assert "强风格化" in prompts[0]


@pytest.mark.asyncio
async def test_final_review_preserves_selected_author_style(monkeypatch):
    from app.workflow_executor import WritingWorkflowExecutor

    executor = WritingWorkflowExecutor()
    executor.llm_client = {"api_key": "k", "base_url": "https://example.com", "model": "demo", "timeout": 60}

    captured = {}

    async def stub_call_llm(prompt, max_tokens=2000):
        captured["prompt"] = prompt
        return "修订后的章节正文" * 300

    monkeypatch.setattr(executor, "_call_llm", stub_call_llm)

    content = "原始章节正文" * 400
    result = await executor._final_review(
        content,
        {"has_issues": True, "issues": [
            "关键段落语感与人物心境表达不够统一，需要强化风格一致性与修辞控制并调整人物心境铺陈，避免整体修辞失衡和情绪失真。",
            "章节收束的整体语气和宿命感表达不足，尾声需要进一步修订并强化孤独感、命运压迫感与回望意味，避免读者对结尾印象过于平。"
        ]},
        style="web_ergen",
        style_strength="strong",
    )

    assert "耳根派" in captured["prompt"]
    assert "人物常带孤独、执念或命运压迫感" in captured["prompt"]
    assert "强风格化" in captured["prompt"]
