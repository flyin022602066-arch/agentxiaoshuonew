import pytest


def test_ending_completeness_detects_incomplete_ending():
    from app.workflow_executor import check_ending_completeness

    # 半句结尾，应该判定为不完整
    incomplete = "两个黑衣人已分开，一人"
    result = check_ending_completeness(incomplete)
    assert result["is_complete"] is False
    assert result["reason"]


def test_ending_completeness_accepts_complete_ending():
    from app.workflow_executor import check_ending_completeness

    # 完整句结尾，应该通过
    complete = "他转过身，消失在夜色中。"
    result = check_ending_completeness(complete)
    assert result["is_complete"] is True


def test_ending_completeness_detects_dangling_structures():
    from app.workflow_executor import check_ending_completeness

    # 悬空结构结尾
    cases = [
        "他正要开口，忽然",
        "只见远方走来一人，",
        "然而事情远没有这么简单",
        "她刚迈出一步，却",
    ]
    for text in cases:
        result = check_ending_completeness(text)
        assert result["is_complete"] is False, f"Should detect incomplete: {text}"


def test_ending_completeness_accepts_suspense_ending():
    from app.workflow_executor import check_ending_completeness

    # 悬念结尾但句子完整
    suspense_cases = [
        "他推开门，里面空无一人。",
        "刀光一闪，血已溅上墙壁。",
        "她没有回答，只是静静地看着他。",
        "远处传来一声钟鸣，仿佛某种预兆。",
    ]
    for text in suspense_cases:
        result = check_ending_completeness(text)
        assert result["is_complete"] is True, f"Should accept suspense ending: {text}"


def test_ending_completeness_rejects_transition_only_endings():
    from app.workflow_executor import check_ending_completeness

    transition_only_cases = [
        "他推开仓库门，朝里面走去。下一秒，他看见前方亮起一盏灯。",
        "她握紧手机，快步走下台阶。紧接着，楼道尽头传来一阵脚步声。",
        "林深把信纸塞进口袋，抬头望向码头。就在这时，黑暗里有人影慢慢走了出来。",
    ]

    for text in transition_only_cases:
        result = check_ending_completeness(text)
        assert result["is_complete"] is False, f"Should reject transition-only ending: {text}"
        assert result["reason"]


def test_build_chapter_plan_requires_local_closure_before_hook():
    from app.workflow_executor import build_chapter_plan

    plan = build_chapter_plan(
        chapter_num=5,
        outline="主角在码头与线人见面，确认父亲失踪案另有隐情。",
        prev_chapters=[],
        style_feedback=None,
    )

    ending_state = plan.get("ending_state") or {}
    plot_state = ending_state.get("plot_state", "")
    hook = ending_state.get("hook", "")
    assert "收束" in plot_state or "收束" in hook
    assert "悬念" in hook


@pytest.mark.asyncio
async def test_workflow_auto_completes_incomplete_ending(monkeypatch):
    from app.workflow_executor import WritingWorkflowExecutor

    executor = WritingWorkflowExecutor()
    executor.llm_client = {"api_key": "k", "base_url": "https://example.com", "model": "demo", "timeout": 60}

    captured = {}

    async def stub_call_llm(prompt, max_tokens=2000):
        captured["prompt"] = prompt
        return "他握紧刀柄，目光如冰。风从巷口灌入，卷起满地落叶。他知道，今夜之后，一切都将不同。远处的钟声敲了三下，夜色更深了。"

    monkeypatch.setattr(executor, "_call_llm", stub_call_llm)

    incomplete_content = "两个黑衣人已分开，一人"
    result = await executor._complete_ending(incomplete_content)

    assert result
    assert len(result) > len(incomplete_content)
    assert "补尾" in captured["prompt"] or "收尾" in captured["prompt"]


@pytest.mark.asyncio
async def test_executor_repairs_transition_only_chapter_endings(monkeypatch):
    from app.workflow_executor import WritingWorkflowExecutor, check_ending_completeness

    executor = WritingWorkflowExecutor()
    executor.llm_client = {"api_key": "k", "base_url": "https://example.com", "model": "demo", "timeout": 60}

    async def stub_previous_chapters(novel_id, current_chapter, count=3):
        return []

    async def stub_refine_outline(outline, style, prev_chapters, macro_plot, protagonist_halo, novel_id, current_chapter, style_strength=None):
        return outline

    async def stub_prepare_characters(novel_id, outline, prev_chapters, world_map, protagonist_halo):
        return {"character_notes": "", "character_state_packet": {}}

    async def stub_write_draft(outline, character_notes, word_count_target, style, prev_chapters, macro_plot, world_map, protagonist_halo, style_strength=None):
        paragraph = (
            "他推开仓库门，潮湿的霉味一下子扑了上来。仓库里堆满了废旧木箱，空气里全是铁锈和旧机油混在一起的气味。"
            "林深把呼吸压得很轻，沿着墙边慢慢往里走，耳边只剩下自己鞋底摩擦水泥地的声音。"
            "他知道信里把他引到这里，绝不只是为了让他看一间空仓库。"
            "头顶一盏坏了一半的白炽灯忽明忽暗，把货架和绳索照出一截一截扭曲的影子。"
            "他走到仓库中央，脚边忽然踢到一个金属盒子，盒盖上沾着已经发黑的血迹。"
            "林深没有立刻伸手，只是盯着那层暗红色看了很久，后背一寸寸绷紧。"
            "风从门外灌进来，带着咸涩的水汽，把地上的旧报纸吹得窸窣作响。"
            "他想起信里那句“想知道父亲失踪那晚发生了什么，就一个人来”，胸口像被什么轻轻撞了一下。"
        )
        return paragraph * 3 + "蹲下身正要去碰。下一秒，他看见前方亮起一盏灯。"

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

    async def stub_polish_dialogue(content, style='default', style_strength=None):
        return content

    async def stub_de_ai(content, style='default', style_strength=None):
        return content

    async def stub_complete_ending(content, style='default', style_strength=None):
        return content + "他停下脚步，没有再往前。那盏灯像是在等他，而他终于知道，自己已经没有退路。"

    async def stub_continue_until_complete(content, chapter_plan, word_count_target, style='default', style_strength=None):
        return content

    monkeypatch.setattr(executor, "_get_previous_chapters", stub_previous_chapters)
    monkeypatch.setattr(executor, "_refine_outline_smart", stub_refine_outline)
    monkeypatch.setattr(executor, "_prepare_characters_smart", stub_prepare_characters)
    monkeypatch.setattr(executor, "_write_draft_smart", stub_write_draft)
    monkeypatch.setattr(executor, "_consistency_check_smart", stub_consistency)
    monkeypatch.setattr(executor, "_final_review", stub_final_review)
    monkeypatch.setattr(executor, "_polish_dialogue", stub_polish_dialogue)
    monkeypatch.setattr(executor, "_de_ai_polish", stub_de_ai)
    monkeypatch.setattr(executor, "_complete_ending", stub_complete_ending)
    monkeypatch.setattr(executor, "_continue_chapter_until_complete", stub_continue_until_complete)

    result = await executor.execute_chapter_workflow(
        novel_id="novel_test",
        chapter_num=1,
        outline="主角进入仓库，发现异常。",
        word_count_target=1200,
        style="default",
    )

    assert result["status"] == "success"
    assert result["content"].endswith("。")
    assert "下一秒" not in result["content"][-25:]
    assert "没有退路" in result["content"]
    ending_check = check_ending_completeness(result["content"])
    assert ending_check["is_complete"] is True
    tail = result["content"][-120:]
    assert any(marker in tail for marker in ["终于", "知道", "没有退路", "停下脚步"])
