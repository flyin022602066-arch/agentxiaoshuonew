import pytest


@pytest.mark.asyncio
async def test_novel_routes_delegate_to_novel_service(client, monkeypatch):
    from app.api import novel_routes

    class StubNovelService:
        def list_novels(self):
            return [{"id": "n1", "title": "测试小说"}]

    monkeypatch.setattr(novel_routes, "get_novel_service", lambda: StubNovelService())

    response = await client.get("/api/novels")
    body = response.json()

    assert response.status_code == 200
    assert body["data"]["novels"][0]["id"] == "n1"


@pytest.mark.asyncio
async def test_writing_routes_delegate_to_writing_service(client, monkeypatch):
    from app.api import writing_routes

    class StubWritingService:
        async def create_chapter_workflow(self, chapter_data, task_id=None):
            return {
                "status": "success",
                "workflow_id": "wf-1",
                "chapter_num": 2,
                "content": "测试正文",
                "word_count": 4,
                "stages_completed": 6,
                "total_stages": 6,
            }

    monkeypatch.setattr(writing_routes, "get_writing_service", lambda: StubWritingService())

    response = await client.post("/api/writing/chapter", json={"novel_id": "n1", "chapter_num": 2, "outline": "测试大纲"})
    body = response.json()

    assert response.status_code == 200
    assert body["status"] == "success"
    assert body["data"]["status"] == "pending"
    assert body["data"]["task_id"]


@pytest.mark.asyncio
async def test_learning_routes_delegate_to_learning_service(client, monkeypatch):
    from app.api import learning_routes

    class StubLearningService:
        def list_analyzed_works(self):
            return {"works": [{"analysis_id": "a1", "title": "示例"}], "total": 1}

    monkeypatch.setattr(learning_routes, "get_learning_service", lambda: StubLearningService())

    response = await client.get("/api/learning/works")
    body = response.json()

    assert response.status_code == 200
    assert body["data"]["works"][0]["analysis_id"] == "a1"
