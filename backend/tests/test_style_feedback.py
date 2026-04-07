import pytest


def test_style_hit_evaluation_scores_matching_keywords():
    from app.workflow_executor import evaluate_style_hit

    content = "灯很冷。刀也很冷。可他的眼睛，比刀更冷。夜色沉沉，人物对白锋利而克制。"
    result = evaluate_style_hit(content, "wuxia_gulong", "strong")

    assert result["style_id"] == "wuxia_gulong"
    assert result["score"] >= 60
    assert result["matched_features"]
    assert result["summary"]


@pytest.mark.asyncio
async def test_consistency_check_returns_style_feedback(monkeypatch):
    from app.workflow_executor import WritingWorkflowExecutor

    executor = WritingWorkflowExecutor()
    executor.llm_client = {"api_key": "k", "base_url": "https://example.com", "model": "demo", "timeout": 60}

    class StubChecker:
        def check(self, content, context):
            return {
                "issues": [],
                "pass": True,
                "total_score": 91,
                "word_count": len(content),
            }

    class StubMemory:
        def save_chapter_memory(self, novel_id, chapter_num, content):
            return None

    monkeypatch.setattr("app.services.quality_checker.QualityChecker", StubChecker)
    monkeypatch.setattr("app.services.story_memory.StoryMemory", StubMemory)

    result = await executor._consistency_check_smart(
        content="灯很冷。刀也很冷。可他的眼睛，比刀更冷。" * 80,
        novel_id="novel-style",
        prev_chapters=[{"chapter_num": 1, "content": "前章内容" * 50}],
        world_map=None,
        protagonist_halo=None,
        chapter_num=2,
        style="wuxia_gulong",
        style_strength="strong",
    )

    assert "style_feedback" in result
    assert result["style_feedback"]["style_id"] == "wuxia_gulong"
    assert result["style_feedback"]["score"] >= 60


@pytest.mark.asyncio
async def test_workflow_result_exposes_style_feedback(monkeypatch):
    from app.workflow_executor import WritingWorkflowExecutor

    executor = WritingWorkflowExecutor()
    executor.llm_client = {"api_key": "k", "base_url": "https://example.com", "model": "demo", "timeout": 60}

    async def stub_prev_chapters(*args, **kwargs):
        return [{"chapter_num": 1, "content": ("灯很冷。刀也很冷。可他的眼睛，比刀更冷。" * 60)}]

    async def stub_refine(*args, **kwargs):
        return "细化大纲"

    async def stub_prepare(*args, **kwargs):
        return {
            "character_notes": "角色设定",
            "character_state_packet": {
                "protagonist": {
                    "name": "林川",
                    "current_goal": "查清黑石秘密",
                    "current_emotion": "警惕",
                    "new_realization": "",
                    "injuries_or_limits": [],
                    "resources": [],
                    "behavior_constraints": ["不得违背既有人物设定"]
                },
                "supporting_characters": [],
                "relationship_shifts": [],
                "absent_but_relevant_characters": []
            }
        }

    async def stub_write(*args, **kwargs):
        return ("灯很冷。刀也很冷。可他的眼睛，比刀更冷。" * 120)

    async def stub_polish(content, style="default"):
        return content

    async def stub_check(*args, **kwargs):
        return {
            "issues": [],
            "has_issues": False,
            "quality_score": 93,
            "word_count": 2200,
            "style_feedback": {
                "style_id": "wuxia_gulong",
                "score": 82,
                "matched_features": ["语言凝练", "气质冷峻"],
                "missing_features": [],
                "summary": "风格命中较强，古龙派短句与冷峻气质表现明显。",
            },
            "review_packet": {
                "fatal_issues": [],
                "important_issues": [],
                "optional_issues": [],
                "scores": {
                    "continuity": 93,
                    "plot_progress": 80,
                    "character_consistency": 88,
                    "style_match": 82,
                    "ending_strength": 75,
                    "naturalness": 85,
                },
                "style_feedback": {
                    "style_id": "wuxia_gulong",
                    "score": 82,
                    "matched_features": ["语言凝练", "气质冷峻"],
                    "missing_features": [],
                    "summary": "风格命中较强，古龙派短句与冷峻气质表现明显。",
                },
                "pass_to_editor": False,
            },
        }

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
        novel_id="novel-style-feedback",
        chapter_num=2,
        outline="测试大纲",
        word_count_target=2200,
        style="wuxia_gulong",
        style_strength="strong",
    )

    assert result["status"] == "success"
    assert result["style_feedback"]["score"] == 82
    assert "古龙派短句与冷峻气质" in result["style_feedback"]["summary"]
    assert result["style_feedback"]["score"] >= 80
    assert result["chapter_plan"]["chapter_num"] == 2
    assert result["chapter_plan"]["must_not_repeat"]
    assert result["next_chapter_baton"]["must_continue_from"]
    assert result["character_state_packet"]["protagonist"]["name"]
    assert result["character_state_packet"]["protagonist"]["current_emotion"]
    assert "不得违背既有人物设定" in result["character_state_packet"]["protagonist"]["behavior_constraints"]
    assert "review_packet" in result
    assert result["review_packet"]["fatal_issues"] == []
    assert result["review_packet"]["scores"]["style_match"] == 82
    assert result["review_packet"]["scores"]["character_consistency"] >= 80


@pytest.mark.asyncio
async def test_executor_rejects_or_repairs_style_drift(monkeypatch):
    from app.workflow_executor import WritingWorkflowExecutor

    executor = WritingWorkflowExecutor()
    executor.llm_client = {"api_key": "k", "base_url": "https://example.com", "model": "demo", "timeout": 60}

    drifted_content = (
        "林川走进院子时，夜已经很深了，可他的眼睛，比刀更冷。"
        "接下来，他开始详细回顾整个局势的发展过程，并且对每一个人的立场进行系统分析。"
        "值得注意的是，眼前发生的一切都说明局面远比表面看上去复杂得多。"
        "由此可见，他接下来的决定将会成为整个事件的重要转折点。"
    ) * 40

    async def stub_prev_chapters(*args, **kwargs):
        return [{"chapter_num": 1, "content": "灯很冷。刀也很冷。可他的眼睛，比刀更冷。" * 60}]

    async def stub_refine(*args, **kwargs):
        return "细化大纲"

    async def stub_prepare(*args, **kwargs):
        return {
            "character_notes": "角色设定",
            "character_state_packet": {
                "protagonist": {
                    "name": "林川",
                    "current_goal": "试探来者身份",
                    "current_emotion": "警惕克制",
                    "new_realization": "",
                    "injuries_or_limits": [],
                    "resources": [],
                    "behavior_constraints": ["不得突然转为解释型长篇独白"],
                },
                "supporting_characters": [],
                "relationship_shifts": [],
                "absent_but_relevant_characters": [],
            },
        }

    async def stub_write(*args, **kwargs):
        return drifted_content

    async def stub_polish(content, style="default", style_strength=None):
        return content

    async def stub_check(*args, **kwargs):
        return {
            "issues": ["章节语感与既定风格差异明显，解释性语句过多，短句冷峻气质被削弱。"],
            "has_issues": True,
            "quality_score": 71,
            "word_count": len(drifted_content),
            "style_feedback": {
                "style_id": "wuxia_gulong",
                "score": 38,
                "matched_features": [],
                "missing_features": ["语言凝练", "气质冷峻"],
                "summary": "风格命中偏弱，文本明显偏向解释性叙述。",
            },
            "review_packet": {
                "fatal_issues": [],
                "important_issues": ["风格漂移明显"],
                "optional_issues": [],
                "scores": {
                    "continuity": 82,
                    "plot_progress": 75,
                    "character_consistency": 78,
                    "style_match": 38,
                    "ending_strength": 70,
                    "naturalness": 74,
                },
                "style_feedback": {
                    "style_id": "wuxia_gulong",
                    "score": 38,
                    "matched_features": [],
                    "missing_features": ["语言凝练", "气质冷峻"],
                    "summary": "风格命中偏弱，文本明显偏向解释性叙述。",
                },
                "pass_to_editor": False,
            },
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
        novel_id="novel-style-drift",
        chapter_num=2,
        outline="主角试探来者身份。",
        word_count_target=2200,
        style="wuxia_gulong",
        style_strength="strong",
    )

    assert result["status"] == "error"
    assert (
        "风格" in result["message"]
        or "style" in result["message"].lower()
        or "漂移" in result["message"]
        or "承接" in result["message"]
    )


@pytest.mark.asyncio
async def test_executor_rejects_or_repairs_character_drift(monkeypatch):
    from app.workflow_executor import WritingWorkflowExecutor

    executor = WritingWorkflowExecutor()
    executor.llm_client = {"api_key": "k", "base_url": "https://example.com", "model": "demo", "timeout": 60}

    ooc_content = (
        "林川原本还记得自己该先观察再动手，可下一刻却突然站到院子中央，拍着手大笑起来。"
        "他甚至主动高声自报家门，像是生怕对方不知道自己是谁。"
        "面对危险，他不但没有压低情绪，反而故意用夸张的语气挑衅所有人。"
        "这一刻的他，和前文那个谨慎、克制的人仿佛完全不是同一个。"
    ) * 30

    async def stub_prev_chapters(*args, **kwargs):
        return [{"chapter_num": 1, "content": "林川一直很谨慎，遇事先观察再动手。" * 60}]

    async def stub_refine(*args, **kwargs):
        return "细化大纲"

    async def stub_prepare(*args, **kwargs):
        return {
            "character_notes": "角色设定",
            "character_state_packet": {
                "protagonist": {
                    "name": "林川",
                    "current_goal": "探清院中埋伏",
                    "current_emotion": "警惕克制",
                    "new_realization": "",
                    "injuries_or_limits": [],
                    "resources": [],
                    "behavior_constraints": ["不得突然张扬自曝身份", "遇险时先观察再行动"],
                },
                "supporting_characters": [],
                "relationship_shifts": [],
                "absent_but_relevant_characters": [],
            },
        }

    async def stub_write(*args, **kwargs):
        return ooc_content

    async def stub_polish(content, style="default", style_strength=None):
        return content

    async def stub_check(*args, **kwargs):
        return {
            "issues": ["人物行为与既定性格明显冲突，当前段落存在OOC风险。"],
            "has_issues": True,
            "quality_score": 74,
            "word_count": len(ooc_content),
            "style_feedback": {
                "style_id": "default",
                "score": 72,
                "matched_features": ["叙事完整"],
                "missing_features": [],
                "summary": "风格基本稳定。",
            },
            "review_packet": {
                "fatal_issues": [],
                "important_issues": ["人物出现明显OOC倾向"],
                "optional_issues": [],
                "scores": {
                    "continuity": 78,
                    "plot_progress": 76,
                    "character_consistency": 35,
                    "style_match": 72,
                    "ending_strength": 70,
                    "naturalness": 74,
                },
                "style_feedback": {
                    "style_id": "default",
                    "score": 72,
                    "matched_features": ["叙事完整"],
                    "missing_features": [],
                    "summary": "风格基本稳定。",
                },
                "pass_to_editor": False,
            },
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
        novel_id="novel-character-drift",
        chapter_num=2,
        outline="主角试探院中埋伏。",
        word_count_target=2200,
        style="default",
    )

    assert result["status"] == "error"
    assert (
        "人物" in result["message"]
        or "OOC" in result["message"]
        or "character" in result["message"].lower()
        or "承接" in result["message"]
    )
