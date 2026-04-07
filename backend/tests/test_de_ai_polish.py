import pytest


def test_ai_pattern_detection_catches_novel_cliches():
    from app.services.quality_checker import QualityChecker

    checker = QualityChecker()

    content = (
        "他深吸一口气，眼中闪过一丝冷意。"
        "嘴角勾起一抹冷笑，心中暗道：这还只是开始。"
        "与此同时，一股莫名的感觉涌上心头。"
        "命运的齿轮开始转动，一场风暴正在酝酿。"
        "谁也没有想到，真正的考验才刚刚到来。"
    )

    patterns = checker._check_ai_patterns(content)
    assert len(patterns) >= 5
    assert any("深吸" in p for p in patterns)
    assert any("眼中闪过" in p for p in patterns)
    assert any("嘴角勾起" in p for p in patterns)
    assert any("心中暗道" in p for p in patterns)
    assert any("命运" in p for p in patterns)


def test_ai_pattern_detection_accepts_natural_writing():
    from app.services.quality_checker import QualityChecker

    checker = QualityChecker()

    content = (
        "他推开门，屋里很暗。"
        "桌上放着一封信，信封已经发黄。"
        "他坐下来，慢慢读完。信是父亲写的，字迹有些抖。"
        "窗外的雨下得更大了。"
    )

    patterns = checker._check_ai_patterns(content)
    assert len(patterns) == 0


def test_ai_pattern_detection_catches_expository_tone():
    from app.services.quality_checker import QualityChecker

    checker = QualityChecker()

    content = (
        "值得注意的是，这件事背后另有隐情。"
        "由此可见，事情远非表面那么简单。"
        "毫无疑问，这是一个转折点。"
    )

    patterns = checker._check_ai_patterns(content)
    assert len(patterns) >= 3


def test_ai_pattern_detection_catches_clustered_template_prose():
    from app.services.quality_checker import QualityChecker

    checker = QualityChecker()

    content = (
        "他不由得一怔，心头微微一沉。"
        "空气仿佛在这一刻凝固，某种预感悄然涌上心头。"
        "他张了张嘴，却一时间说不出话来。"
    )

    patterns = checker._check_ai_patterns(content)
    assert len(patterns) >= 3


@pytest.mark.asyncio
async def test_de_ai_polish_returns_content(monkeypatch):
    from app.workflow_executor import WritingWorkflowExecutor

    executor = WritingWorkflowExecutor()
    executor.llm_client = {"api_key": "k", "base_url": "https://example.com", "model": "demo", "timeout": 60}

    captured = {}

    async def stub_call_llm(prompt, max_tokens=2000):
        captured["prompt"] = prompt
        return "他推开门，屋里很暗。桌上放着一封信。他坐下来读完，窗外的雨更大了。"

    monkeypatch.setattr(executor, "_call_llm", stub_call_llm)

    ai_content = "他深吸一口气，眼中闪过一丝冷意。"
    result = await executor._de_ai_polish(ai_content, style="default", style_strength="medium")

    assert result
    assert "去AI" in captured["prompt"] or "AI痕迹" in captured["prompt"] or "AI腔" in captured["prompt"]
    assert "眼中闪过一丝" in captured["prompt"]
    assert "嘴角勾起一抹" in captured["prompt"]
    assert "深吸一口气" in captured["prompt"]


@pytest.mark.asyncio
async def test_executor_triggers_de_ai_polish_for_high_pattern_density(monkeypatch):
    from app.workflow_executor import WritingWorkflowExecutor

    executor = WritingWorkflowExecutor()
    executor.llm_client = {"api_key": "k", "base_url": "https://example.com", "model": "demo", "timeout": 60}

    ai_heavy_content = (
        "他深吸一口气，眼中闪过一丝冷意。"
        "嘴角勾起一抹冷笑，心中暗道：这还只是开始。"
        "与此同时，一股莫名的感觉涌上心头。"
        "命运的齿轮开始转动，一场风暴正在酝酿。"
    ) * 20
    polished_paragraph = (
        "他抬手按了按眉骨，没有立刻说话。窗缝漏进来的风把纸页掀起一角，他伸手压住，指尖微微发凉。"
        "屋里安静得过分，连木桌轻轻晃动的声音都听得见。"
        "事情走到这一步，已经没法再往后退了。"
        "他把信纸重新折好，塞回口袋，目光慢慢沉下来。"
    )
    polished_content = polished_paragraph * 12

    de_ai_called = {"value": False}

    async def stub_previous_chapters(novel_id, current_chapter, count=3):
        return []

    async def stub_refine_outline(outline, style, prev_chapters, macro_plot, protagonist_halo, novel_id, current_chapter, style_strength=None):
        return outline

    async def stub_prepare_characters(novel_id, outline, prev_chapters, world_map, protagonist_halo):
        return {"character_notes": "", "character_state_packet": {}}

    async def stub_write_draft(outline, character_notes, word_count_target, style, prev_chapters, macro_plot, world_map, protagonist_halo, style_strength=None):
        return ai_heavy_content

    async def stub_polish_dialogue(content, style='default', style_strength=None):
        return content

    async def stub_de_ai(content, style='default', style_strength=None):
        de_ai_called["value"] = True
        return polished_content

    async def stub_consistency(content, novel_id, prev_chapters, world_map, protagonist_halo, chapter_num, style='default', style_strength=None):
        return {
            "issues": [],
            "has_issues": False,
            "quality_score": 90,
            "word_count": len(content),
            "style_feedback": {"score": 80, "matched_features": [], "missing_features": [], "summary": "ok"},
            "review_packet": {"fatal_issues": [], "important_issues": [], "optional_issues": [], "scores": {}, "style_feedback": {}, "editor_patch_brief": [], "pass_to_editor": False},
        }

    async def stub_final_review(content, check_result, style='default', style_strength=None):
        return content

    monkeypatch.setattr(executor, "_get_previous_chapters", stub_previous_chapters)
    monkeypatch.setattr(executor, "_refine_outline_smart", stub_refine_outline)
    monkeypatch.setattr(executor, "_prepare_characters_smart", stub_prepare_characters)
    monkeypatch.setattr(executor, "_write_draft_smart", stub_write_draft)
    monkeypatch.setattr(executor, "_polish_dialogue", stub_polish_dialogue)
    monkeypatch.setattr(executor, "_de_ai_polish", stub_de_ai)
    monkeypatch.setattr(executor, "_consistency_check_smart", stub_consistency)
    monkeypatch.setattr(executor, "_final_review", stub_final_review)

    result = await executor.execute_chapter_workflow(
        novel_id="novel_de_ai",
        chapter_num=1,
        outline="主角察觉阴谋逼近。",
        word_count_target=1800,
        style="default",
    )

    assert result["status"] == "success"
    assert de_ai_called["value"] is True
    assert result["content"] == polished_content


@pytest.mark.asyncio
async def test_executor_skips_de_ai_polish_for_natural_prose(monkeypatch):
    from app.workflow_executor import WritingWorkflowExecutor

    executor = WritingWorkflowExecutor()
    executor.llm_client = {"api_key": "k", "base_url": "https://example.com", "model": "demo", "timeout": 60}

    natural_content = (
        "他推开门，屋里很暗。桌上放着一封信，信封已经发黄。"
        "他坐下来，慢慢把信拆开，看了一遍，又低头重新看第二遍。"
        "窗外的雨下得更大了，玻璃被敲得细碎发响。"
        "信是父亲写的，字迹有些抖，到最后几行甚至断开了。"
    ) * 18

    de_ai_called = {"value": False}

    async def stub_previous_chapters(novel_id, current_chapter, count=3):
        return []

    async def stub_refine_outline(outline, style, prev_chapters, macro_plot, protagonist_halo, novel_id, current_chapter, style_strength=None):
        return outline

    async def stub_prepare_characters(novel_id, outline, prev_chapters, world_map, protagonist_halo):
        return {"character_notes": "", "character_state_packet": {}}

    async def stub_write_draft(outline, character_notes, word_count_target, style, prev_chapters, macro_plot, world_map, protagonist_halo, style_strength=None):
        return natural_content

    async def stub_polish_dialogue(content, style='default', style_strength=None):
        return content

    async def stub_de_ai(content, style='default', style_strength=None):
        de_ai_called["value"] = True
        return content

    async def stub_consistency(content, novel_id, prev_chapters, world_map, protagonist_halo, chapter_num, style='default', style_strength=None):
        return {
            "issues": [],
            "has_issues": False,
            "quality_score": 90,
            "word_count": len(content),
            "style_feedback": {"score": 80, "matched_features": [], "missing_features": [], "summary": "ok"},
            "review_packet": {"fatal_issues": [], "important_issues": [], "optional_issues": [], "scores": {}, "style_feedback": {}, "editor_patch_brief": [], "pass_to_editor": False},
        }

    async def stub_final_review(content, check_result, style='default', style_strength=None):
        return content

    monkeypatch.setattr(executor, "_get_previous_chapters", stub_previous_chapters)
    monkeypatch.setattr(executor, "_refine_outline_smart", stub_refine_outline)
    monkeypatch.setattr(executor, "_prepare_characters_smart", stub_prepare_characters)
    monkeypatch.setattr(executor, "_write_draft_smart", stub_write_draft)
    monkeypatch.setattr(executor, "_polish_dialogue", stub_polish_dialogue)
    monkeypatch.setattr(executor, "_de_ai_polish", stub_de_ai)
    monkeypatch.setattr(executor, "_consistency_check_smart", stub_consistency)
    monkeypatch.setattr(executor, "_final_review", stub_final_review)

    result = await executor.execute_chapter_workflow(
        novel_id="novel_de_ai",
        chapter_num=1,
        outline="主角读到父亲留下的旧信。",
        word_count_target=1800,
        style="default",
    )

    assert result["status"] == "success"
    assert de_ai_called["value"] is False
    assert result["content"] == natural_content
