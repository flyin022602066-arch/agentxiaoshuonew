from pathlib import Path

import pytest


def test_default_novel_database_path_points_to_backend_data():
    from app.novel_db import get_default_novel_db_path

    db_path = get_default_novel_db_path()

    assert db_path.name == "novels.db"
    assert db_path.parent.name == "data"
    assert db_path.parent.parent.name == "backend"


def test_config_default_sqlite_path_matches_novel_database_source():
    from app.config import DEFAULT_NOVEL_DB_PATH, MemoryConfig
    from app.novel_db import get_default_novel_db_path

    assert Path(DEFAULT_NOVEL_DB_PATH).resolve() == get_default_novel_db_path().resolve()
    assert Path(MemoryConfig().sqlite_path).resolve() == get_default_novel_db_path().resolve()


@pytest.mark.asyncio
async def test_health_database_check_reports_runtime_novel_database_path():
    from app.api.health import check_database
    from app.novel_db import get_default_novel_db_path

    result = await check_database()

    assert result["status"] == "ok"
    assert Path(result["path"]).resolve() == get_default_novel_db_path().resolve()
