import pytest


def test_publishability_scan_flags_graphic_and_explicit_risk():
    from app.workflow_executor import scan_publishability_risks

    content = (
        "他把她按在墙上，手直接探进衣服里，动作粗暴得没有任何停顿。"
        "刀锋划开皮肉，血和碎肉一下子溅了出来，连骨头都翻了出来。"
        "他点燃粉末吸了下去，整个人瞬间兴奋得发抖。"
    )

    result = scan_publishability_risks(content)

    assert result["blocked"] is True
    categories = {item["category"] for item in result["hits"]}
    assert "explicit_sexual" in categories
    assert "graphic_violence" in categories
    assert "drug_abuse" in categories


def test_publishability_scan_accepts_benign_conflict_prose():
    from app.workflow_executor import scan_publishability_risks

    content = (
        "他握紧刀柄，却没有立刻出手。"
        "屋里的人都屏住了呼吸，谁也不知道下一秒会是谁先动。"
        "雨还在下，窗纸被风吹得发响。"
    )

    result = scan_publishability_risks(content)

    assert result["blocked"] is False
    assert result["hits"] == []


def test_writing_prompt_includes_platform_friendly_constraints():
    from app.services.style_learner import StyleLearner

    learner = StyleLearner()
    prompt = learner.get_platform_prompt(
        platform="fanqiao",
        outline="主角夜探废楼，发现隐藏线索。",
        prev_content="前章结尾：主角听到楼上传来脚步声。",
        character_notes="主角：警惕、克制。",
    )

    assert "前文衔接" in prompt
    assert "角色状态" in prompt
    assert "不要大段环境描写" in prompt or "节奏快" in prompt
    assert "请开始创作" in prompt


def test_publishability_scan_reports_fixable_categories():
    from app.workflow_executor import scan_publishability_risks

    content = "他把她按在墙上，手直接探进衣服里。"
    result = scan_publishability_risks(content)

    assert result["blocked"] is True
    assert result["hits"][0]["category"] == "explicit_sexual"


def test_publishability_scan_reports_unrepairable_categories():
    from app.workflow_executor import scan_publishability_risks

    content = "刀锋划开皮肉，血和碎肉一起炸开，骨头都翻了出来。"
    result = scan_publishability_risks(content)

    assert result["blocked"] is True
    assert result["hits"][0]["category"] == "graphic_violence"


@pytest.mark.asyncio
async def test_executor_repairs_fixable_publish_risks(monkeypatch):
    from app.workflow_executor import WritingWorkflowExecutor

    executor = WritingWorkflowExecutor()
    executor.llm_client = {"api_key": "k", "base_url": "https://example.com", "model": "demo", "timeout": 60}

    risky_content = (
        "他把她按在墙上，手直接探进衣服里。"
        "她猛地一挣，肩膀撞在墙上，呼吸一下子乱了。"
        "门外忽然有人经过，两人同时僵住。"
    ) * 30

    repaired_content = risky_content.replace("手直接探进衣服里", "伸手去拽她的衣袖").replace("按在墙上", "逼到墙边")

    async def stub_prev(*args, **kwargs):
        return []

    async def stub_refine(*args, **kwargs):
        return "细化大纲"

    async def stub_prepare(*args, **kwargs):
        return {"character_notes": "角色设定", "character_state_packet": {}}

    async def stub_write(*args, **kwargs):
        return risky_content

    async def stub_polish(content, style="default", style_strength=None):
        return content

    async def stub_consistency(*args, **kwargs):
        return {
            "issues": [],
            "has_issues": False,
            "quality_score": 88,
            "word_count": len(risky_content),
            "style_feedback": {"style_id": "default", "score": 75, "matched_features": [], "missing_features": [], "summary": "ok"},
            "review_packet": {"fatal_issues": [], "important_issues": [], "optional_issues": [], "scores": {"continuity": 80, "plot_progress": 78, "character_consistency": 80, "style_match": 75, "ending_strength": 72, "naturalness": 76}, "style_feedback": {}, "pass_to_editor": False},
        }

    async def stub_final(content, check_result, style="default", style_strength=None):
        return content

    async def stub_publishability_polish(content, hits):
        return repaired_content

    monkeypatch.setattr(executor, "_get_previous_chapters", stub_prev)
    monkeypatch.setattr(executor, "_refine_outline_smart", stub_refine)
    monkeypatch.setattr(executor, "_prepare_characters_smart", stub_prepare)
    monkeypatch.setattr(executor, "_write_draft_smart", stub_write)
    monkeypatch.setattr(executor, "_polish_dialogue", stub_polish)
    monkeypatch.setattr(executor, "_consistency_check_smart", stub_consistency)
    monkeypatch.setattr(executor, "_final_review", stub_final)
    monkeypatch.setattr(executor, "_publishability_polish", stub_publishability_polish, raising=False)

    result = await executor.execute_chapter_workflow(
        novel_id="novel-publishable",
        chapter_num=1,
        outline="人物在危险局势里互相试探。",
        word_count_target=1800,
        style="default",
    )

    assert result["status"] == "success"
    assert "探进衣服里" not in result["content"]
    assert "逼到墙边" in result["content"]


@pytest.mark.asyncio
async def test_executor_blocks_unrepairable_publish_risk(monkeypatch):
    from app.workflow_executor import WritingWorkflowExecutor

    executor = WritingWorkflowExecutor()
    executor.llm_client = {"api_key": "k", "base_url": "https://example.com", "model": "demo", "timeout": 60}

    risky_content = (
        "刀锋划开皮肉，血和碎肉一起炸开，骨头都翻了出来。"
        "他踩着满地血浆继续往前走，脚下还发出黏腻的声响。"
    ) * 20

    async def stub_prev(*args, **kwargs):
        return []

    async def stub_refine(*args, **kwargs):
        return "细化大纲"

    async def stub_prepare(*args, **kwargs):
        return {"character_notes": "角色设定", "character_state_packet": {}}

    async def stub_write(*args, **kwargs):
        return risky_content

    async def stub_polish(content, style="default", style_strength=None):
        return content

    async def stub_consistency(*args, **kwargs):
        return {
            "issues": [],
            "has_issues": False,
            "quality_score": 86,
            "word_count": len(risky_content),
            "style_feedback": {"style_id": "default", "score": 72, "matched_features": [], "missing_features": [], "summary": "ok"},
            "review_packet": {"fatal_issues": [], "important_issues": [], "optional_issues": [], "scores": {"continuity": 80, "plot_progress": 79, "character_consistency": 81, "style_match": 72, "ending_strength": 73, "naturalness": 74}, "style_feedback": {}, "pass_to_editor": False},
        }

    async def stub_final(content, check_result, style="default", style_strength=None):
        return content

    monkeypatch.setattr(executor, "_get_previous_chapters", stub_prev)
    monkeypatch.setattr(executor, "_refine_outline_smart", stub_refine)
    monkeypatch.setattr(executor, "_prepare_characters_smart", stub_prepare)
    monkeypatch.setattr(executor, "_write_draft_smart", stub_write)
    monkeypatch.setattr(executor, "_polish_dialogue", stub_polish)
    monkeypatch.setattr(executor, "_consistency_check_smart", stub_consistency)
    monkeypatch.setattr(executor, "_final_review", stub_final)

    result = await executor.execute_chapter_workflow(
        novel_id="novel-publishable-block",
        chapter_num=1,
        outline="主角进入屠宰般的现场。",
        word_count_target=1800,
        style="default",
    )

    assert result["status"] == "error"
    assert "平台" in result["message"] or "风险" in result["message"] or "publish" in result["message"].lower()
