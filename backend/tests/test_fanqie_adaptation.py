import pytest


def test_fanqie_check_flags_slow_opening():
    from app.workflow_executor import evaluate_fanqie_feel

    content = (
        "清晨的风很轻，院子里的树叶一片片往下落。"
        "主角站在窗边想了很多往事，回忆也像雾一样漫了上来。"
        "他先想起旧年离家的那一天，又想起少年时在巷子里见过的雪。"
        "过了很久，故事还没有真正进入眼前的事件。"
    )

    result = evaluate_fanqie_feel(content)

    assert result["pass"] is False
    assert any(issue["type"] == "opening_speed" for issue in result["issues"])


def test_fanqie_check_flags_weak_hook():
    from app.workflow_executor import evaluate_fanqie_feel

    content = (
        "主角终于回到住处，简单洗了把脸。"
        "他把桌上的纸张整理好，又把窗户轻轻关上。"
        "夜慢慢深了，屋里安静下来。"
        "这一章就在平稳收束里结束，没有新的危险、疑问或拉力。"
    ) * 20

    result = evaluate_fanqie_feel(content)

    assert result["pass"] is False
    assert any(issue["type"] == "hook_strength" for issue in result["issues"])


def test_fanqie_check_accepts_fast_conflict_driven_chapter():
    from app.workflow_executor import evaluate_fanqie_feel

    content = (
        "林川刚翻过院墙，屋里就亮起了灯。"
        "他脚还没站稳，里面的人已经冷声叫出了他的名字。"
        "对方明显早有准备，门口和后窗同时传来脚步声。"
        "林川没有退路，只能先抢一步把人质拽到身前。"
        "可就在他以为自己抓住主动时，那人却笑着说了一句：你终于来了。"
    ) * 20

    result = evaluate_fanqie_feel(content)

    assert result["pass"] is True
    assert result["score"] >= 60


def test_fanqie_prompt_requires_fast_entry_and_strong_hook():
    from app.services.style_learner import StyleLearner

    learner = StyleLearner()
    prompt = learner.get_platform_prompt(
        platform="fanqiao",
        outline="主角夜探废楼，发现埋伏。",
        prev_content="前章结尾：楼上传来第二个人的脚步声。",
        character_notes="主角：警惕、克制。",
    )

    assert "节奏快" in prompt
    assert "冲突强" in prompt
    assert "悬念多" in prompt
    assert "爽点密集" in prompt


@pytest.mark.asyncio
async def test_executor_repairs_underpowered_fanqie_chapter(monkeypatch):
    from app.workflow_executor import WritingWorkflowExecutor

    executor = WritingWorkflowExecutor()
    executor.llm_client = {"api_key": "k", "base_url": "https://example.com", "model": "demo", "timeout": 60}

    slow_content = (
        "林川回到住处后，先把外套挂好，又慢慢擦去靴底的泥。"
        "他坐在桌边，回想着白天遇到的每一个细节，试图理清其中的先后关系。"
        "屋里很安静，灯火微微摇晃，连呼吸声都显得缓慢。"
        "他知道事情不简单，但这一章的推进明显还不够快。"
    ) * 30

    adapted_content = (
        "林川刚推门进屋，桌上的油灯就自己晃了一下。"
        "他还没来得及放下外套，窗外已经有人影贴了上来，门板也被人从外面按住。"
        "这不是回家，而是第二轮追杀的开始，他再慢一步就会被堵死在屋里。"
        "可当他拔刀转身时，门外那人却先低声说出一句：东西已经在你屋里了。"
    ) * 20

    async def stub_prev(*args, **kwargs):
        return []

    async def stub_refine(*args, **kwargs):
        return "细化大纲"

    async def stub_prepare(*args, **kwargs):
        return {"character_notes": "角色设定", "character_state_packet": {}}

    async def stub_write(*args, **kwargs):
        return slow_content

    async def stub_polish(content, style="default", style_strength=None):
        return content

    async def stub_consistency(*args, **kwargs):
        return {
            "issues": [],
            "has_issues": False,
            "quality_score": 86,
            "word_count": len(slow_content),
            "style_feedback": {"style_id": "default", "score": 72, "matched_features": [], "missing_features": [], "summary": "ok"},
            "review_packet": {"fatal_issues": [], "important_issues": [], "optional_issues": [], "scores": {"continuity": 80, "plot_progress": 72, "character_consistency": 82, "style_match": 72, "ending_strength": 60, "naturalness": 78}, "style_feedback": {}, "pass_to_editor": False},
        }

    async def stub_final(content, check_result, style="default", style_strength=None):
        return content

    async def stub_fanqie_polish(content, diagnostics):
        return adapted_content

    monkeypatch.setattr(executor, "_get_previous_chapters", stub_prev)
    monkeypatch.setattr(executor, "_refine_outline_smart", stub_refine)
    monkeypatch.setattr(executor, "_prepare_characters_smart", stub_prepare)
    monkeypatch.setattr(executor, "_write_draft_smart", stub_write)
    monkeypatch.setattr(executor, "_polish_dialogue", stub_polish)
    monkeypatch.setattr(executor, "_consistency_check_smart", stub_consistency)
    monkeypatch.setattr(executor, "_final_review", stub_final)
    monkeypatch.setattr(executor, "_fanqie_adaptation_polish", stub_fanqie_polish, raising=False)

    result = await executor.execute_chapter_workflow(
        novel_id="novel-fanqie",
        chapter_num=1,
        outline="主角回屋后发现敌人已经追到门外。",
        word_count_target=1800,
        style="fanqiao",
    )

    assert result["status"] == "success"
    assert result["content"] == adapted_content


@pytest.mark.asyncio
async def test_executor_blocks_chapter_that_still_lacks_fanqie_feel(monkeypatch):
    from app.workflow_executor import WritingWorkflowExecutor

    executor = WritingWorkflowExecutor()
    executor.llm_client = {"api_key": "k", "base_url": "https://example.com", "model": "demo", "timeout": 60}

    weak_content = (
        "夜色很安静，主角坐在桌边回想往事。"
        "他想着很多过去发生的事情，思绪慢慢飘远。"
        "外面的风吹过屋檐，除此之外什么都没有发生。"
        "这一章结束得很平，也没有特别强的推动。"
    ) * 30

    async def stub_prev(*args, **kwargs):
        return []

    async def stub_refine(*args, **kwargs):
        return "细化大纲"

    async def stub_prepare(*args, **kwargs):
        return {"character_notes": "角色设定", "character_state_packet": {}}

    async def stub_write(*args, **kwargs):
        return weak_content

    async def stub_polish(content, style="default", style_strength=None):
        return content

    async def stub_consistency(*args, **kwargs):
        return {
            "issues": [],
            "has_issues": False,
            "quality_score": 84,
            "word_count": len(weak_content),
            "style_feedback": {"style_id": "fanqiao", "score": 70, "matched_features": [], "missing_features": [], "summary": "ok"},
            "review_packet": {"fatal_issues": [], "important_issues": [], "optional_issues": [], "scores": {"continuity": 80, "plot_progress": 68, "character_consistency": 82, "style_match": 70, "ending_strength": 55, "naturalness": 78}, "style_feedback": {}, "pass_to_editor": False},
        }

    async def stub_final(content, check_result, style="default", style_strength=None):
        return content

    async def stub_fanqie_polish(content, diagnostics):
        return content

    monkeypatch.setattr(executor, "_get_previous_chapters", stub_prev)
    monkeypatch.setattr(executor, "_refine_outline_smart", stub_refine)
    monkeypatch.setattr(executor, "_prepare_characters_smart", stub_prepare)
    monkeypatch.setattr(executor, "_write_draft_smart", stub_write)
    monkeypatch.setattr(executor, "_polish_dialogue", stub_polish)
    monkeypatch.setattr(executor, "_consistency_check_smart", stub_consistency)
    monkeypatch.setattr(executor, "_final_review", stub_final)
    monkeypatch.setattr(executor, "_fanqie_adaptation_polish", stub_fanqie_polish, raising=False)

    result = await executor.execute_chapter_workflow(
        novel_id="novel-fanqie-block",
        chapter_num=1,
        outline="主角独自在屋里沉思。",
        word_count_target=1800,
        style="fanqiao",
    )

    assert result["status"] == "error"
    assert "番茄" in result["message"] or "平台" in result["message"] or "Fanqie" in result["message"]
