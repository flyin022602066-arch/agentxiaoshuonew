import pytest


def test_qimao_check_flags_emotion_thin_prose():
    from app.workflow_executor import evaluate_qimao_feel

    content = (
        "他回到房间，坐下，喝水，看窗外。"
        "情绪几乎没有起伏，动作只是依次发生。"
        "这一段把事情交代清楚了，但读者很难感到人物心里在动。"
    ) * 10

    result = evaluate_qimao_feel(content)

    assert result["pass"] is False
    assert any(issue["type"] == "emotion_continuity" for issue in result["issues"])


def test_qimao_check_flags_thin_scene_texture():
    from app.workflow_executor import evaluate_qimao_feel

    content = (
        "她走进屋子，坐下，说话，然后离开。"
        "场景只交代动作，没有温度、气味、光线或其他质感。"
    ) * 15

    result = evaluate_qimao_feel(content)

    assert result["pass"] is False
    assert any(issue["type"] == "scene_texture" for issue in result["issues"])


def test_qimao_check_accepts_gentle_layered_chapter():
    from app.workflow_executor import evaluate_qimao_feel

    content = (
        "她推门进去时，屋里还残着一点药味，窗边那盆栀子花在夜风里轻轻晃了一下。"
        "他说话并不急，只是把茶盏往她手边推了推，像是怕她一路赶来会冷。"
        "她本想直接问出口，可看到他指节上那道还没结好的伤，心里又微微顿了一下。"
        "屋里安静了几息，谁都没有先提旧事，可那份压在两人之间的情绪却越来越沉。"
        "直到他低声问她一句：这些年，你是不是一直在怪我。"
    ) * 15

    result = evaluate_qimao_feel(content)

    assert result["pass"] is True
    assert result["score"] >= 60


def test_qimao_prompt_requires_emotion_texture_and_layered_interaction():
    from app.services.style_learner import StyleLearner

    learner = StyleLearner()
    prompt = learner.get_platform_prompt(
        platform="qimao",
        outline="她深夜回到旧宅，试探旧人真实态度。",
        prev_content="前章结尾：他没有正面回答，只把茶盏推到她手边。",
        character_notes="主角：克制、迟疑。",
    )

    assert "描写细腻" in prompt
    assert "情感丰富" in prompt
    assert "人物立体" in prompt
    assert "节奏适中" in prompt


@pytest.mark.asyncio
async def test_executor_repairs_underpowered_qimao_chapter(monkeypatch):
    from app.workflow_executor import WritingWorkflowExecutor

    executor = WritingWorkflowExecutor()
    executor.llm_client = {"api_key": "k", "base_url": "https://example.com", "model": "demo", "timeout": 60}

    thin_content = (
        "她进门，坐下，看着他。"
        "他说了几句，她听着，没有太多反应。"
        "屋子里很安静，事情往下推，但情绪和质感都偏薄。"
    ) * 40

    adapted_content = (
        "她推门进去时，屋里还残着一点药味，靠窗那盏灯把桌角照得微微发暖。"
        "他说话并不急，只是把茶盏往她手边推了推，像是怕她赶夜路回来会冷。"
        "她本想立刻问出口，可指尖碰到杯沿时，心里却忽然软了一下。"
        "屋里安静了几息，谁都没有先提旧事，可那层压在两人之间的情绪却越来越沉。"
        "直到她垂下眼，终究还是没有把那句藏了很多年的责问说出口。"
    ) * 20

    async def stub_prev(*args, **kwargs):
        return []

    async def stub_refine(*args, **kwargs):
        return "细化大纲"

    async def stub_prepare(*args, **kwargs):
        return {"character_notes": "角色设定", "character_state_packet": {}}

    async def stub_write(*args, **kwargs):
        return thin_content

    async def stub_polish(content, style="default", style_strength=None):
        return content

    async def stub_consistency(*args, **kwargs):
        return {
            "issues": [],
            "has_issues": False,
            "quality_score": 86,
            "word_count": len(thin_content),
            "style_feedback": {"style_id": "default", "score": 74, "matched_features": [], "missing_features": [], "summary": "ok"},
            "review_packet": {"fatal_issues": [], "important_issues": [], "optional_issues": [], "scores": {"continuity": 82, "plot_progress": 74, "character_consistency": 84, "style_match": 74, "ending_strength": 72, "naturalness": 76}, "style_feedback": {}, "pass_to_editor": False},
        }

    async def stub_final(content, check_result, style="default", style_strength=None):
        return content

    async def stub_qimao_polish(content, diagnostics):
        return adapted_content

    monkeypatch.setattr(executor, "_get_previous_chapters", stub_prev)
    monkeypatch.setattr(executor, "_refine_outline_smart", stub_refine)
    monkeypatch.setattr(executor, "_prepare_characters_smart", stub_prepare)
    monkeypatch.setattr(executor, "_write_draft_smart", stub_write)
    monkeypatch.setattr(executor, "_polish_dialogue", stub_polish)
    monkeypatch.setattr(executor, "_consistency_check_smart", stub_consistency)
    monkeypatch.setattr(executor, "_final_review", stub_final)
    monkeypatch.setattr(executor, "_qimao_adaptation_polish", stub_qimao_polish, raising=False)

    result = await executor.execute_chapter_workflow(
        novel_id="novel-qimao",
        chapter_num=1,
        outline="她深夜回到旧宅，试探旧人真实态度。",
        word_count_target=1800,
        style="qimao",
    )

    assert result["status"] == "success"
    assert result["content"] == adapted_content


@pytest.mark.asyncio
async def test_executor_blocks_chapter_that_still_lacks_qimao_feel(monkeypatch):
    from app.workflow_executor import WritingWorkflowExecutor

    executor = WritingWorkflowExecutor()
    executor.llm_client = {"api_key": "k", "base_url": "https://example.com", "model": "demo", "timeout": 60}

    weak_content = (
        "她回屋，坐下，喝水。"
        "他说了几句，她点头。"
        "这一段把事情交代完了，但没有什么余味。"
    ) * 40

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
            "style_feedback": {"style_id": "qimao", "score": 70, "matched_features": [], "missing_features": [], "summary": "ok"},
            "review_packet": {"fatal_issues": [], "important_issues": [], "optional_issues": [], "scores": {"continuity": 80, "plot_progress": 72, "character_consistency": 82, "style_match": 70, "ending_strength": 60, "naturalness": 78}, "style_feedback": {}, "pass_to_editor": False},
        }

    async def stub_final(content, check_result, style="default", style_strength=None):
        return content

    async def stub_qimao_polish(content, diagnostics):
        return content

    monkeypatch.setattr(executor, "_get_previous_chapters", stub_prev)
    monkeypatch.setattr(executor, "_refine_outline_smart", stub_refine)
    monkeypatch.setattr(executor, "_prepare_characters_smart", stub_prepare)
    monkeypatch.setattr(executor, "_write_draft_smart", stub_write)
    monkeypatch.setattr(executor, "_polish_dialogue", stub_polish)
    monkeypatch.setattr(executor, "_consistency_check_smart", stub_consistency)
    monkeypatch.setattr(executor, "_final_review", stub_final)
    monkeypatch.setattr(executor, "_qimao_adaptation_polish", stub_qimao_polish, raising=False)

    result = await executor.execute_chapter_workflow(
        novel_id="novel-qimao-block",
        chapter_num=1,
        outline="她回屋后继续试探他的态度。",
        word_count_target=1800,
        style="qimao",
    )

    assert result["status"] == "error"
    assert "七猫" in result["message"] or "平台" in result["message"] or "Qimao" in result["message"]
