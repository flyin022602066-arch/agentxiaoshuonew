import pytest


def test_evaluate_chapter_completion_flags_underdeveloped_chapter():
    from app.workflow_executor import evaluate_chapter_completion

    chapter_plan = {
        "chapter_goal": "确认祭坛与黑石联系，并引出新的敌方线索",
        "must_advance": ["确认祭坛与黑石联系", "引出新的敌方线索"],
        "ending_state": {"plot_state": "主角得到新线索并形成下一章接口"}
    }

    result = evaluate_chapter_completion(
        content="林川进入祭坛外围，黑石微微发热，但他还没有真正发现更多东西。",
        chapter_plan=chapter_plan,
        word_count_target=3000,
    )

    assert result["is_complete"] is False
    assert result["reasons"]


@pytest.mark.asyncio
async def test_workflow_uses_continuation_pass_when_chapter_not_semantically_complete(monkeypatch):
    from app.workflow_executor import WritingWorkflowExecutor

    executor = WritingWorkflowExecutor()
    executor.llm_client = {"api_key": "k", "base_url": "https://example.com", "model": "demo", "timeout": 60}

    async def stub_prev_chapters(*args, **kwargs):
        return [{"chapter_num": 1, "content": "前章内容" * 60}]

    async def stub_refine(*args, **kwargs):
        return "确认祭坛与黑石联系，并引出新的敌方线索"

    async def stub_prepare(*args, **kwargs):
        return {
            "character_notes": "角色设定",
            "character_state_packet": {
                "protagonist": {
                    "name": "林川",
                    "current_goal": "查清黑石秘密",
                    "current_emotion": "警惕"
                },
                "supporting_characters": [],
                "relationship_shifts": [],
                "absent_but_relevant_characters": []
            }
        }

    async def stub_write(*args, **kwargs):
        return "林川进入祭坛外围，黑石微微发热，但他还没有真正发现更多东西。" * 40

    async def stub_polish(content, style="default"):
        return content

    async def stub_check(*args, **kwargs):
        return {
            "issues": [],
            "has_issues": False,
            "quality_score": 90,
            "word_count": 1200,
            "style_feedback": {"style_id": "default", "score": 70, "matched_features": [], "missing_features": [], "summary": ""},
            "review_packet": {"fatal_issues": [], "important_issues": [], "optional_issues": [], "scores": {}, "style_feedback": {}, "pass_to_editor": False},
        }

    async def stub_final(content, check_result, style="default", style_strength=None):
        return content

    async def stub_continue(content, chapter_plan, word_count_target, style="default", style_strength=None):
        return content + "\n\n祭坛石壁上的纹路终于与黑石呼应，林川也在地面残痕里发现了新的追踪标记。他意识到敌人真正想要的不是自己，而是黑石背后的秘密。夜风穿过废墟，他知道，下一步只能继续深入。"

    monkeypatch.setattr(executor, "_get_previous_chapters", stub_prev_chapters)
    monkeypatch.setattr(executor, "_refine_outline_smart", stub_refine)
    monkeypatch.setattr(executor, "_prepare_characters_smart", stub_prepare)
    monkeypatch.setattr(executor, "_write_draft_smart", stub_write)
    monkeypatch.setattr(executor, "_polish_dialogue", stub_polish)
    monkeypatch.setattr(executor, "_consistency_check_smart", stub_check)
    monkeypatch.setattr(executor, "_final_review", stub_final)
    monkeypatch.setattr(executor, "_continue_chapter_until_complete", stub_continue)

    result = await executor.execute_chapter_workflow(
        novel_id="novel-semantic",
        chapter_num=2,
        outline="测试大纲",
        word_count_target=3000,
        style="default",
    )

    assert result["status"] == "success"
    assert "真正想要的不是自己" in result["content"]
    assert result["word_count"] > 900
