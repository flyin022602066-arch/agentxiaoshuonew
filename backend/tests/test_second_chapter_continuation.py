import pytest


def test_next_chapter_baton_requires_continuation_not_replay():
    from app.workflow_executor import build_next_chapter_baton, build_chapter_plan

    baton = build_next_chapter_baton("主角在码头发现有人提前等他。")
    plan = build_chapter_plan(
        chapter_num=2,
        outline="承接码头相见后的局势推进。",
        prev_chapters=[{"chapter_num": 1, "content": "主角在码头发现有人提前等他。"}],
        style_feedback=None,
    )

    must_continue_from = baton.get("must_continue_from", "")
    carry_forward_emotion = baton.get("carry_forward_emotion", "")
    forbidden_backtracks = baton.get("forbidden_backtracks", []) or []
    must_not_repeat = plan.get("must_not_repeat", []) or []

    assert "延续" in must_continue_from or "延续" in carry_forward_emotion
    assert any("禁止重复" in item or "禁止回头重写" in item for item in forbidden_backtracks)
    assert any("禁止重复" in item for item in must_not_repeat)


@pytest.mark.asyncio
async def test_executor_rejects_second_chapter_replay(monkeypatch):
    from app.workflow_executor import WritingWorkflowExecutor

    executor = WritingWorkflowExecutor()
    executor.llm_client = {"api_key": "k", "base_url": "https://example.com", "model": "demo", "timeout": 60}

    repeated_content = (
        "林川拖着伤腿穿过废土集市，身后始终有两道影子不远不近地缀着。"
        "他不敢回头，只能一边装作若无其事，一边借着摊位与棚布遮挡自己的行踪。"
        "直到他拐进一条堆满废铁的窄巷，那两个人才终于露出真正的杀意。"
        "林川借着地形反手一击，把最前面的追兵撞翻在地，自己也被刀锋划开了肩膀。"
        "他咬着牙冲出巷口，正准备继续逃。下一秒，前方有人提前等在了那里。"
    ) * 4

    async def stub_previous_chapters(novel_id, current_chapter, count=3):
        return [{"chapter_num": 1, "title": "第一章", "content": repeated_content, "next_chapter_baton": {"must_continue_from": "前方有人提前等在了那里。", "carry_forward_emotion": "危险逼近", "carry_forward_hooks": ["等他的人是谁"], "forbidden_backtracks": ["禁止回头重写上一章已完成的主事件"]}}]

    async def stub_refine_outline(outline, style, prev_chapters, macro_plot, protagonist_halo, novel_id, current_chapter, style_strength=None):
        return outline

    async def stub_prepare_characters(novel_id, outline, prev_chapters, world_map, protagonist_halo):
        return {"character_notes": "", "character_state_packet": {}}

    async def stub_write_draft(outline, character_notes, word_count_target, style, prev_chapters, macro_plot, world_map, protagonist_halo, style_strength=None):
        return repeated_content

    async def stub_polish_dialogue(content, style='default', style_strength=None):
        return content

    async def stub_de_ai(content, style='default', style_strength=None):
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
        novel_id="novel_continuity",
        chapter_num=2,
        outline="承接前方突然出现的人，推进新的危机。",
        word_count_target=1800,
        style="default",
    )

    assert result["status"] == "error"
    assert "过于相似" in result["message"] or "重复" in result["message"]


@pytest.mark.asyncio
async def test_executor_logs_warning_instead_of_failing_second_chapter_carryover(monkeypatch):
    from app.workflow_executor import WritingWorkflowExecutor

    executor = WritingWorkflowExecutor()
    executor.llm_client = {"api_key": "k", "base_url": "https://example.com", "model": "demo", "timeout": 60}

    previous_content = (
        "林川追到码头尽头时，雨已经下大了。"
        "那人始终背对着他，手里提着一盏旧灯，像是早就知道他会来。"
        "海风卷着雾气扑上栈桥，木板在脚下轻轻摇晃。"
        "林川刚要开口，对方却先叫出了他的名字。"
    ) * 6

    unrelated_opening = (
        "第二天清晨，城里照常开市，街边小贩吆喝不停。"
        "林川坐在面摊前慢慢喝汤，仿佛昨夜什么都没有发生。"
        "他抬头看了看天色，又低头数了数手里的铜钱。"
        "周围人声鼎沸，连风里都带着油饼和热汤的味道。"
    ) * 6

    async def stub_previous_chapters(novel_id, current_chapter, count=3):
        return [{
            "chapter_num": 1,
            "title": "第一章",
            "content": previous_content,
            "next_chapter_baton": {
                "must_continue_from": "对方先在码头雨夜里叫出了林川的名字。",
                "carry_forward_emotion": "警惕和压迫感持续升级",
                "carry_forward_hooks": ["叫出名字的人到底是谁"],
                "forbidden_backtracks": ["禁止跳回平静日常开场", "禁止无视码头对峙的直接后果"],
            },
        }]

    async def stub_refine_outline(outline, style, prev_chapters, macro_plot, protagonist_halo, novel_id, current_chapter, style_strength=None):
        return outline

    async def stub_prepare_characters(novel_id, outline, prev_chapters, world_map, protagonist_halo):
        return {"character_notes": "", "character_state_packet": {}}

    async def stub_write_draft(outline, character_notes, word_count_target, style, prev_chapters, macro_plot, world_map, protagonist_halo, style_strength=None):
        return unrelated_opening

    async def stub_polish_dialogue(content, style='default', style_strength=None):
        return content

    async def stub_de_ai(content, style='default', style_strength=None):
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
        novel_id="novel_continuity",
        chapter_num=2,
        outline="承接码头对峙，揭示叫出名字之人的来意。",
        word_count_target=1800,
        style="default",
    )

    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_executor_allows_second_chapter_to_continue_despite_carryover_miss(monkeypatch):
    from app.workflow_executor import WritingWorkflowExecutor

    executor = WritingWorkflowExecutor()
    executor.llm_client = {"api_key": "k", "base_url": "https://example.com", "model": "demo", "timeout": 60}

    previous_content = (
        "林川追到码头尽头时，雨已经下大了。"
        "那人始终背对着他，手里提着一盏旧灯，像是早就知道他会来。"
        "海风卷着雾气扑上栈桥，木板在脚下轻轻摇晃。"
        "林川刚要开口，对方却先叫出了他的名字。"
    ) * 6

    weak_carryover_opening = (
        "天刚亮时，林川已经离开了码头，沿着潮湿石阶走向城内。"
        "他没有停下脚步，只是把昨夜听见的那句话反复咀嚼。"
        "风还带着海腥味，衣角上的潮气提醒他危险并未真正远去。"
        "街巷渐渐热闹起来，但他心里的警惕始终没有散去。"
    ) * 6

    async def stub_previous_chapters(novel_id, current_chapter, count=3):
        return [{
            "chapter_num": 1,
            "title": "第一章",
            "content": previous_content,
            "next_chapter_baton": {
                "must_continue_from": "对方先在码头雨夜里叫出了林川的名字。",
                "carry_forward_emotion": "警惕和压迫感持续升级",
                "carry_forward_hooks": ["叫出名字的人到底是谁"],
                "forbidden_backtracks": ["禁止跳回平静日常开场", "禁止无视码头对峙的直接后果"],
            },
        }]

    async def stub_refine_outline(outline, style, prev_chapters, macro_plot, protagonist_halo, novel_id, current_chapter, style_strength=None):
        return outline

    async def stub_prepare_characters(novel_id, outline, prev_chapters, world_map, protagonist_halo):
        return {"character_notes": "", "character_state_packet": {}}

    async def stub_write_draft(outline, character_notes, word_count_target, style, prev_chapters, macro_plot, world_map, protagonist_halo, style_strength=None):
        return weak_carryover_opening

    async def stub_polish_dialogue(content, style='default', style_strength=None):
        return content

    async def stub_de_ai(content, style='default', style_strength=None):
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
        novel_id="novel_continuity",
        chapter_num=2,
        outline="承接码头对峙后的压力，推进新的危机。",
        word_count_target=1800,
        style="default",
    )

    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_writing_service_falls_back_when_segment_generation_returns_empty(monkeypatch, tmp_path):
    from app.services.writing_service import WritingService
    from app.novel_db import NovelDatabase
    from app.services.chapter_service import ChapterService

    db = NovelDatabase(str(tmp_path / "novels.db"))
    novel_id = db.create_novel(
        "第二章测试",
        "玄幻",
        "简介",
        settings={
            "world_map": {"world_name": "九州"},
            "macro_plot": {"volumes": [{"volume_num": 1, "main_goal": "崛起", "conflict": "追兵逼近"}]},
            "character_system": {"protagonist": {"name": "林川", "goal": "活下去", "background": "废土孤儿", "personality": ["冷静"]}},
            "hook_network": {"short_term": [{"description": "黑石秘密", "reveal_chapter": 5}]},
        },
    )
    db.create_chapter(novel_id, 1, "第一章", "开场遭遇")
    db.update_chapter(novel_id, 1, content="第一章正文内容" * 200, title="第一章", outline="开场遭遇", status="published")

    class StubExecutor:
        llm_client = {"api_key": "k"}

        async def execute_chapter_workflow(self, **kwargs):
            return {
                "status": "success",
                "workflow_id": "wf-2",
                "chapter_num": 2,
                "content": (
                    "第二章一开场，林川还记得医院门口那阵逼近的脚步声。"
                    "他没有回头，而是借着雨棚塌下来的阴影继续往前躲。"
                    "追兵并没有被甩开，反而比刚才更近了。"
                    "他一边压着呼吸，一边判断下一条巷口能不能反杀。"
                    "这一次，他不能再像第一章那样只顾着逃。"
                ) * 60,
                "word_count": 1600,
            }

    monkeypatch.setattr("app.services.writing_service.get_novel_database", lambda: db)
    monkeypatch.setattr("app.services.writing_service.get_workflow_executor", lambda: StubExecutor())
    monkeypatch.setattr("app.services.writing_service.get_chapter_service", lambda: ChapterService(str(tmp_path / "novels.db")))

    service = WritingService()
    result = await service.create_chapter_workflow({
        "novel_id": novel_id,
        "chapter_num": 2,
        "outline": "主角离开医院遭遇追兵",
        "word_count_target": 2500,
        "style": "default",
        "style_context": {"style_id": "default", "strength": "medium"},
    })

    assert result["status"] == "success"
    chapter = db.get_chapter(novel_id, 2)
    assert chapter is not None
    assert chapter["content"].startswith("第二章一开场")
    assert "医院门口" in chapter["content"]
    assert "追兵" in chapter["content"]
    assert "第一章正文内容" not in chapter["content"][:120]


@pytest.mark.asyncio
async def test_chapter_generator_single_pass_fallback_when_segments_empty(monkeypatch):
    from app.services.chapter_generator import ChapterGenerator

    async def stub_llm(prompt, max_tokens):
        if "拆分成" in prompt:
            return "---\n第一段大纲\n---\n第二段大纲"
        return ""

    generator = ChapterGenerator(stub_llm)

    async def stub_single_pass(*args, **kwargs):
        return "回退生成的完整章节正文" * 180

    monkeypatch.setattr(generator, "_generate_single_pass", stub_single_pass)

    content = await generator.generate_chapter(
        outline="第二章大纲",
        word_count_target=2500,
        prev_chapters=[{"chapter_num": 1, "content": "第一章正文" * 100}],
        character_notes="主角：林川",
        world_map={"world_name": "九州"},
        style="default",
    )

    assert content.startswith("回退生成的完整章节正文")
    assert len(content) > 500
