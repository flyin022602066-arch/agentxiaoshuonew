import pytest


@pytest.mark.asyncio
async def test_refine_outline_smart_uses_current_novel_and_chapter_for_story_memory(monkeypatch):
    from app.workflow_executor import WritingWorkflowExecutor

    executor = WritingWorkflowExecutor()
    executor.llm_client = {"api_key": "k", "base_url": "https://example.com", "model": "demo", "timeout": 60}
    executor.runtime_provider = {"name": "provider-name"}

    captured = {}

    class StubMemory:
        def get_story_context(self, novel_id, current_chapter):
            captured["novel_id"] = novel_id
            captured["current_chapter"] = current_chapter
            return {"recent_summary": "第2章：主角逃出医院"}

        def format_context_for_prompt(self, context):
            return "故事记忆摘要"

    async def stub_refine_outline(outline, style):
        captured["outline"] = outline
        captured["style"] = style
        return "细化后的大纲"

    monkeypatch.setattr("app.services.story_memory.StoryMemory", StubMemory)
    monkeypatch.setattr(executor, "_refine_outline", stub_refine_outline)

    result = await executor._refine_outline_smart(
        outline="第三章：主角摆脱追兵后发现黑石异动",
        style="default",
        prev_chapters=[{"chapter_num": 2, "content": "第二章：医院追逐战结束，主角带着黑石逃离。"}],
        macro_plot={"volumes": [{"main_goal": "崛起"}]},
        protagonist_halo={"name": "林川"},
        novel_id="novel-123",
        current_chapter=3,
    )

    assert result == "细化后的大纲"
    assert captured["novel_id"] == "novel-123"
    assert captured["current_chapter"] == 3
    assert "第二章" in captured["outline"]


@pytest.mark.asyncio
async def test_consistency_check_smart_saves_memory_for_current_chapter(monkeypatch):
    from app.workflow_executor import WritingWorkflowExecutor

    executor = WritingWorkflowExecutor()
    executor.llm_client = {"api_key": "k", "base_url": "https://example.com", "model": "demo", "timeout": 60}

    captured = {}

    class StubQualityChecker:
        def check(self, content, context):
            captured["quality_prev_content"] = context.get("prev_content")
            return {
                "issues": [],
                "pass": True,
                "total_score": 88,
                "word_count": len(content),
            }

    class StubMemory:
        def save_chapter_memory(self, novel_id, chapter_num, content):
            captured["saved_novel_id"] = novel_id
            captured["saved_chapter_num"] = chapter_num
            captured["saved_content"] = content

    monkeypatch.setattr("app.services.quality_checker.QualityChecker", StubQualityChecker)
    monkeypatch.setattr("app.services.story_memory.StoryMemory", StubMemory)

    result = await executor._consistency_check_smart(
        content="第三章正文" * 300,
        novel_id="novel-xyz",
        prev_chapters=[{"chapter_num": 2, "content": "第二章正文" * 120}],
        world_map={"world_name": "九州"},
        protagonist_halo={"name": "林川"},
        chapter_num=3,
    )

    assert result["has_issues"] is False
    assert captured["quality_prev_content"].startswith("第二章正文")
    assert captured["saved_novel_id"] == "novel-xyz"
    assert captured["saved_chapter_num"] == 3
    assert captured["saved_content"].startswith("第三章正文")


@pytest.mark.asyncio
async def test_third_chapter_workflow_uses_second_chapter_as_latest_reference(monkeypatch):
    from app.workflow_executor import WritingWorkflowExecutor

    executor = WritingWorkflowExecutor()
    executor.llm_client = {"api_key": "k", "base_url": "https://example.com", "model": "demo", "timeout": 60}

    captured = {}

    async def stub_prev_chapters(novel_id, current_chapter, count=3):
        assert novel_id == "novel-3"
        assert current_chapter == 3
        return [
            {"chapter_num": 1, "title": "第一章", "content": "第一章：林川在废墟中捡到黑石。"},
            {"chapter_num": 2, "title": "第二章", "content": "第二章：林川摆脱医院追兵，带着黑石逃到城外。"},
        ]

    async def stub_refine(outline, style, prev_chapters, macro_plot, protagonist_halo, novel_id, current_chapter):
        captured["refine_prev_chapters"] = prev_chapters
        captured["refine_novel_id"] = novel_id
        captured["refine_current_chapter"] = current_chapter
        return "第三章细化大纲：主角在城外发现黑石异动，不能重复医院追逐。"

    async def stub_prepare(novel_id, outline, prev_chapters, world_map, protagonist_halo):
        captured["prepare_prev_last"] = prev_chapters[-1]["chapter_num"]
        return "角色设定"

    async def stub_write(outline, character_notes, word_count_target, style, prev_chapters, macro_plot, world_map, protagonist_halo):
        captured["write_outline"] = outline
        captured["write_prev_last"] = prev_chapters[-1]["chapter_num"]
        captured["write_prev_last_content"] = prev_chapters[-1]["content"]
        return "第三章正文：林川没有重复医院追逐，而是在城外研究黑石异动。" * 30

    async def stub_polish(content, style="default"):
        return content

    async def stub_check(content, novel_id, prev_chapters, world_map, protagonist_halo, chapter_num, **kwargs):
        captured["check_prev_last"] = prev_chapters[-1]["chapter_num"]
        captured["check_chapter_num"] = chapter_num
        return {"issues": [], "has_issues": False, "quality_score": 92, "word_count": len(content)}

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
        novel_id="novel-3",
        chapter_num=3,
        outline="第三章：承接第二章结尾，推进黑石主线",
        word_count_target=2200,
        style="default",
        macro_plot={"volumes": [{"main_goal": "查明黑石秘密"}]},
        world_map={"world_name": "九州"},
        protagonist_halo={"name": "林川"},
    )

    assert result["status"] == "success"
    assert captured["refine_novel_id"] == "novel-3"
    assert captured["refine_current_chapter"] == 3
    assert captured["prepare_prev_last"] == 2
    assert captured["write_prev_last"] == 2
    assert captured["check_prev_last"] == 2
    assert captured["check_chapter_num"] == 3
    assert "第二章：林川摆脱医院追兵" in captured["write_prev_last_content"]
    assert "不能重复医院追逐" in captured["write_outline"]


@pytest.mark.asyncio
async def test_workflow_rejects_content_that_is_too_similar_to_previous_chapter(monkeypatch):
    from app.workflow_executor import WritingWorkflowExecutor

    executor = WritingWorkflowExecutor()
    executor.llm_client = {"api_key": "k", "base_url": "https://example.com", "model": "demo", "timeout": 60}

    previous_content = (
        "第二章：林川在医院走廊狂奔，身后追兵紧咬不放。"
        "他翻过窗台，带着黑石坠入雨夜，最后逃向城外废桥。"
    ) * 40
    duplicated_content = previous_content + "\n\n他只是把刚才发生的事又重复说了一遍。"

    async def stub_prev_chapters(novel_id, current_chapter, count=3):
        return [{"chapter_num": 2, "title": "第二章", "content": previous_content}]

    async def stub_refine(*args, **kwargs):
        return "第三章细化大纲"

    async def stub_prepare(*args, **kwargs):
        return "角色设定"

    async def stub_write(*args, **kwargs):
        return duplicated_content

    async def stub_polish(content, style="default"):
        return content

    async def stub_check(content, novel_id, prev_chapters, world_map, protagonist_halo, chapter_num, **kwargs):
        return {"issues": [], "has_issues": False, "quality_score": 91, "word_count": len(content)}

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
        novel_id="novel-dup",
        chapter_num=3,
        outline="第三章：承接追兵事件后推进黑石秘密",
        word_count_target=2200,
        style="default",
    )

    assert result["status"] == "error"
    assert "重复" in result["message"] or "相似" in result["message"]


@pytest.mark.asyncio
async def test_workflow_allows_distinct_content_when_similarity_is_low(monkeypatch):
    from app.workflow_executor import WritingWorkflowExecutor

    executor = WritingWorkflowExecutor()
    executor.llm_client = {"api_key": "k", "base_url": "https://example.com", "model": "demo", "timeout": 60}

    previous_content = (
        "第二章：林川摆脱追兵后躲进废桥下，在雨夜中暂时喘息。"
        "黑石在掌心发烫，却还没有真正显露力量。"
    ) * 35
    distinct_content = (
        "第三章：天亮后，林川在城外废桥旁发现黑石表面浮现古老纹路。"
        "他循着纹路指引进入废弃祭坛，第一次听见石中低语，故事主线开始真正推进。"
    ) * 30

    async def stub_prev_chapters(novel_id, current_chapter, count=3):
        return [{"chapter_num": 2, "title": "第二章", "content": previous_content}]

    async def stub_refine(*args, **kwargs):
        return "第三章细化大纲：调查黑石异动，进入祭坛。"

    async def stub_prepare(*args, **kwargs):
        return "角色设定"

    async def stub_write(*args, **kwargs):
        return distinct_content

    async def stub_polish(content, style="default"):
        return content

    async def stub_check(content, novel_id, prev_chapters, world_map, protagonist_halo, chapter_num, **kwargs):
        return {"issues": [], "has_issues": False, "quality_score": 93, "word_count": len(content)}

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
        novel_id="novel-ok",
        chapter_num=3,
        outline="第三章：黑石异动引出新地图",
        word_count_target=2200,
        style="default",
    )

    assert result["status"] == "success"
    assert result["content"].startswith("第三章：天亮后")


@pytest.mark.asyncio
async def test_generate_chapter_outline_returns_post_chapter_outline_summary(monkeypatch):
    from app.workflow_executor import WritingWorkflowExecutor

    executor = WritingWorkflowExecutor()
    executor.llm_client = {"api_key": "k", "base_url": "https://example.com", "model": "demo", "timeout": 60}

    async def stub_call_llm(prompt, max_tokens=2000):
        return """本章标题：第三章 祭坛异动
核心事件：林川发现黑石异动后进入祭坛外围，逼近新的秘密。
情节发展：
1. 林川确认上一章逃亡后的落脚点不再安全。
2. 黑石出现新的纹路，引导他靠近祭坛。
3. 他在祭坛外围发现新的机关与追兵线索。
4. 章节结尾留下更大的谜团。"""

    monkeypatch.setattr(executor, "_call_llm", stub_call_llm)

    result = await executor.generate_chapter_outline(
        novel_title="测试书",
        chapter_num=3,
        overall_outline="承接上一章推进黑石主线",
        context={
            "recent_chapters": [
                {
                    "chapter_num": 2,
                    "title": "第二章",
                    "outline": "医院追逐后逃离",
                    "content_summary": "林川摆脱追兵后逃到城外，黑石出现异动。",
                }
            ]
        },
    )

    assert result["outline"].startswith("本章标题：第三章 祭坛异动")
    assert result["outline_summary"] == "林川发现黑石异动后进入祭坛外围，逼近新的秘密。"


@pytest.mark.asyncio
async def test_writing_service_saves_extracted_outline_summary_as_outline(monkeypatch, tmp_path):
    from app.services.writing_service import WritingService
    from app.novel_db import NovelDatabase

    db = NovelDatabase(str(tmp_path / "novels.db"))
    novel_id = db.create_novel("续写测试", "玄幻", "简介")
    db.create_chapter(novel_id, 2, "第二章", "旧大纲")

    captured = {}

    class StubExecutor:
        llm_client = {"api_key": "k"}

        async def execute_chapter_workflow(self, **kwargs):
            return {
                "status": "success",
                "content": "第三章正文" * 200,
                "word_count": 800,
                "outline_summary": "第三章：祭坛异动暴露新的追兵线索，林川决定继续深入。",
            }

    class StubChapterService:
        def save_chapter(self, **kwargs):
            captured["saved"] = kwargs
            return kwargs

    monkeypatch.setattr("app.services.writing_service.get_novel_database", lambda: db)
    monkeypatch.setattr("app.services.writing_service.get_workflow_executor", lambda: StubExecutor())
    monkeypatch.setattr("app.services.writing_service.get_chapter_service", lambda: StubChapterService())

    service = WritingService()
    result = await service.create_chapter_workflow(
        {
            "novel_id": novel_id,
            "chapter_num": 3,
            "outline": "承接前文继续推进",
            "word_count_target": 2200,
            "style": "default",
        }
    )

    assert result["status"] == "success"
    assert captured["saved"]["outline"] == "第三章：祭坛异动暴露新的追兵线索，林川决定继续深入。"
