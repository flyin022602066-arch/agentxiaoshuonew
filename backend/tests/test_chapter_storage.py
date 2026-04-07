import pytest

from app.services.chapter_service import ChapterService


def test_save_chapter_persists_to_database_single_source(tmp_path):
    service = ChapterService(db_path=tmp_path / "novels.db")
    novel_id = service.create_novel("测试小说")

    service.save_chapter(
        novel_id=novel_id,
        chapter_num=1,
        title="第一章",
        outline="开篇",
        content="这里是正文",
        status="draft",
    )

    chapter = service.get_chapter(novel_id, 1)

    assert chapter["title"] == "第一章"
    assert chapter["outline"] == "开篇"
    assert chapter["content"] == "这里是正文"
    assert chapter["word_count"] == len("这里是正文")


def test_save_chapter_updates_existing_record_instead_of_creating_file_copy(tmp_path):
    service = ChapterService(db_path=tmp_path / "novels.db")
    novel_id = service.create_novel("测试小说")
    service.save_chapter(novel_id=novel_id, chapter_num=1, title="第一章", content="旧内容")

    service.save_chapter(novel_id=novel_id, chapter_num=1, title="第一章修订", content="新内容")

    chapters = service.list_chapters(novel_id)
    chapter = service.get_chapter(novel_id, 1)

    assert len(chapters) == 1
    assert chapter["title"] == "第一章修订"
    assert chapter["content"] == "新内容"


def test_delete_chapter_removes_record_and_updates_stats(tmp_path):
    service = ChapterService(db_path=tmp_path / "novels.db")
    novel_id = service.create_novel("测试小说")
    service.save_chapter(novel_id=novel_id, chapter_num=1, title="第一章", content="正文一")
    service.save_chapter(novel_id=novel_id, chapter_num=2, title="第二章", content="正文二")

    deleted = service.delete_chapter(novel_id, 1)
    remaining = service.list_chapters(novel_id)

    assert deleted is True
    assert [chapter["chapter_num"] for chapter in remaining] == [2]
    assert service.db.get_novel_stats(novel_id)["total_chapters"] == 1


@pytest.mark.asyncio
async def test_writing_endpoints_share_same_database_source(client, tmp_path, monkeypatch):
    from app.api import novel_routes, writing_routes
    from app import novel_db
    from app.services.chapter_service import ChapterService
    from app.services import writing_service as writing_service_module

    service = ChapterService(db_path=tmp_path / "novels.db")
    novel_id = service.create_novel("接口测试小说")
    monkeypatch.setattr(novel_routes, "get_chapter_service", lambda: service)
    monkeypatch.setattr(novel_db, "get_novel_database", lambda: service.db)

    class StubWritingService:
        def get_chapter(self, project_id, chapter_num):
            return service.get_chapter(project_id, chapter_num)

        def update_chapter(self, project_id, chapter_num, chapter_data):
            return service.save_chapter(
                novel_id=project_id,
                chapter_num=chapter_num,
                title=chapter_data.get("title", ""),
                outline=chapter_data.get("outline", ""),
                content=chapter_data.get("content", ""),
                status=chapter_data.get("status", "draft"),
            )

    monkeypatch.setattr(writing_routes, "get_writing_service", lambda: StubWritingService())
    monkeypatch.setattr(writing_service_module, "get_novel_database", lambda: service.db)

    service.create_chapter(novel_id, 1, title="第一章", outline="开篇")

    update_response = await client.put(
        f"/api/writing/chapter/{novel_id}/1",
        json={"title": "第一章", "outline": "开篇", "content": "统一正文", "status": "draft"},
    )
    assert update_response.status_code == 200

    read_response = await client.get(f"/api/novels/{novel_id}/chapters/1")
    body = read_response.json()

    assert body["status"] == "success"
    assert body["data"]["content"] == "统一正文"
    assert body["data"]["outline"] == "开篇"


@pytest.mark.asyncio
async def test_writing_get_endpoint_reads_same_chapter_data_as_novel_endpoint(client, tmp_path, monkeypatch):
    from app.api import novel_routes, writing_routes
    from app.services.chapter_service import ChapterService

    service = ChapterService(db_path=tmp_path / "novels.db")
    novel_id = service.create_novel("接口测试小说")
    service.save_chapter(novel_id=novel_id, chapter_num=3, title="第三章", outline="纲要", content="共享内容")
    monkeypatch.setattr(novel_routes, "get_chapter_service", lambda: service)

    class StubWritingService:
        def get_chapter(self, project_id, chapter_num):
            return service.get_chapter(project_id, chapter_num)

    monkeypatch.setattr(writing_routes, "get_writing_service", lambda: StubWritingService())

    novel_response = await client.get(f"/api/novels/{novel_id}/chapters/3")
    writing_response = await client.get(f"/api/writing/chapter/{novel_id}/3")

    assert novel_response.json()["data"]["content"] == writing_response.json()["data"]["content"]
    assert novel_response.json()["data"]["title"] == writing_response.json()["data"]["title"]


@pytest.mark.asyncio
async def test_delete_chapter_endpoint_returns_success(client, tmp_path, monkeypatch):
    from app.api import novel_routes
    from app import novel_db
    from app.services.chapter_service import ChapterService

    service = ChapterService(db_path=tmp_path / "novels.db")
    novel_id = service.create_novel("删除接口测试")
    service.save_chapter(novel_id=novel_id, chapter_num=1, title="第一章", content="待删除")

    monkeypatch.setattr(novel_routes, "get_chapter_service", lambda: service)
    monkeypatch.setattr(novel_db, "get_novel_database", lambda: service.db)

    response = await client.delete(f"/api/novels/{novel_id}/chapters/1")
    body = response.json()

    assert response.status_code == 200
    assert body["success"] is True
    assert service.get_chapter(novel_id, 1) is None
