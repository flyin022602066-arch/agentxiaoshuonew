import pytest


@pytest.mark.asyncio
async def test_export_single_fanqiao_variant():
    from app.services.writing_service import WritingService

    service = WritingService()

    class StubChapterService:
        def get_chapter(self, novel_id, chapter_num):
            return {
                "novel_id": novel_id,
                "chapter_num": chapter_num,
                "title": "第1章",
                "content": "原始章节内容",
            }

    service.chapter_service = StubChapterService()  # type: ignore[assignment]

    result = await service.export_chapter_variants(novel_id="n1", chapter_num=1, target="fanqiao")

    variants = result.get("variants") or []
    assert result["target"] == "fanqiao"
    assert len(variants) == 1
    assert variants[0]["platform"] == "fanqiao"


@pytest.mark.asyncio
async def test_export_single_qimao_variant():
    from app.services.writing_service import WritingService

    service = WritingService()

    class StubChapterService:
        def get_chapter(self, novel_id, chapter_num):
            return {
                "novel_id": novel_id,
                "chapter_num": chapter_num,
                "title": "第1章",
                "content": "原始章节内容",
            }

    service.chapter_service = StubChapterService()  # type: ignore[assignment]

    result = await service.export_chapter_variants(novel_id="n1", chapter_num=1, target="qimao")

    variants = result.get("variants") or []
    assert result["target"] == "qimao"
    assert len(variants) == 1
    assert variants[0]["platform"] == "qimao"


@pytest.mark.asyncio
async def test_export_both_platform_variants():
    from app.services.writing_service import WritingService

    service = WritingService()

    class StubChapterService:
        def get_chapter(self, novel_id, chapter_num):
            return {
                "novel_id": novel_id,
                "chapter_num": chapter_num,
                "title": "第1章",
                "content": "原始章节内容",
            }

    service.chapter_service = StubChapterService()  # type: ignore[assignment]

    result = await service.export_chapter_variants(novel_id="n1", chapter_num=1, target="both")

    assert result["target"] == "both"
    assert len(result["variants"]) == 2
    platforms = {item["platform"] for item in result["variants"]}
    assert platforms == {"fanqiao", "qimao"}


@pytest.mark.asyncio
async def test_export_response_includes_platform_metadata():
    from app.services.writing_service import WritingService

    service = WritingService()

    class StubChapterService:
        def get_chapter(self, novel_id, chapter_num):
            return {
                "novel_id": novel_id,
                "chapter_num": chapter_num,
                "title": "第2章",
                "content": "原始章节内容",
            }

    service.chapter_service = StubChapterService()  # type: ignore[assignment]

    result = await service.export_chapter_variants(novel_id="novel-1", chapter_num=2, target="both")

    assert result["novel_id"] == "novel-1"
    assert result["chapter_num"] == 2
    assert result["target"] == "both"
    assert all("platform" in item for item in result["variants"])


@pytest.mark.asyncio
async def test_export_does_not_mutate_saved_chapter():
    from app.services.writing_service import WritingService

    service = WritingService()

    source = {
        "novel_id": "novel-1",
        "chapter_num": 2,
        "title": "第2章",
        "content": "原始章节内容",
    }

    class StubChapterService:
        def get_chapter(self, novel_id, chapter_num):
            return dict(source)

    service.chapter_service = StubChapterService()  # type: ignore[assignment]

    before_chapter = service.chapter_service.get_chapter("novel-1", 2)
    assert before_chapter is not None
    before = before_chapter["content"]
    await service.export_chapter_variants(novel_id="novel-1", chapter_num=2, target="both")
    after_chapter = service.chapter_service.get_chapter("novel-1", 2)
    assert after_chapter is not None
    after = after_chapter["content"]

    assert before == after
