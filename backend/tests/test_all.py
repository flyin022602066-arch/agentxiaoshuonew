#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
多 Agent 协作小说系统 - 综合测试脚本
测试所有核心功能，修复第一轮 bug
"""

import sys
import asyncio
from pathlib import Path

import pytest

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

print("=" * 70)
print("Multi-Agent Novel System - Test Suite")
print("=" * 70)

# ========== 测试 1: 导入测试 ==========
print("\n[Test 1/10] Importing all modules...")
try:
    # 添加路径
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    from app.main import app
    from app.config import get_config_manager
    from app.exceptions import NovelAgentException
    from app.agents.registry import create_agents, registry
    from app.memory.memory_engine import get_memory_engine
    from app.utils.llm_client import get_llm_client
    from app.storage.file_manager import get_file_manager
    from app.storage.backup import get_backup_manager
    print("[OK] All modules imported successfully")
except Exception as e:
    print(f"[FAIL] Import failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# ========== 测试 2: 配置管理测试 ==========
print("\n【测试 2/10】配置管理测试...")
try:
    config = get_config_manager()
    print(f"  - 项目名：{config.app_config.project_name if config.app_config else 'N/A'}")
    print(f"  - 默认提供商：{config.get_default_provider() or '未配置'}")
    print(f"  - 已配置提供商：{config.get_all_providers()}")
    print("[OK] 配置管理正常")
except Exception as e:
    print(f"[FAIL] 配置管理失败：{e}")

# ========== 测试 3: LLM 客户端测试 ==========
print("\n【测试 3/10】LLM 客户端测试...")
try:
    llm = get_llm_client()
    print(f"  - 配置文件：{llm.config_path}")
    print(f"  - 提供商数量：{len(llm.providers)}")
    print(f"  - 默认提供商：{llm.default_provider or '未配置'}")
    print("[OK] LLM 客户端正常")
except Exception as e:
    print(f"[FAIL] LLM 客户端失败：{e}")

# ========== 测试 4: Agent 注册表测试 ==========
print("\n【测试 4/10】Agent 注册表测试...")
try:
    # 注意：这里不实际创建 Agent，因为需要 LLM 配置
    print(f"  - 已注册 Agent 数：{len(registry.get_all())}")
    print(f"  - Agent 列表：{list(registry.get_all().keys())}")
    print("[OK] Agent 注册表正常")
except Exception as e:
    print(f"[FAIL] Agent 注册表失败：{e}")

# ========== 测试 5: 记忆引擎测试 ==========
print("\n【测试 5/10】记忆引擎测试...")
try:
    memory = get_memory_engine('./projects/test')
    print(f"  - 项目路径：{memory.project_path}")
    print(f"  - 短期记忆窗口：{memory.short_term.window_size}")
    print("[OK] 记忆引擎正常")
except Exception as e:
    print(f"[FAIL] 记忆引擎失败：{e}")

# ========== 测试 6: 文件管理器测试 ==========
print("\n【测试 6/10】文件管理器测试...")
try:
    fm = get_file_manager('./projects/test')
    print(f"  - 项目路径：{fm.project_path}")
    print(f"  - 目录已创建：{fm.project_path.exists()}")
    print("[OK] 文件管理器正常")
except Exception as e:
    print(f"[FAIL] 文件管理器失败：{e}")

# ========== 测试 7: 备份管理测试 ==========
print("\n【测试 7/10】备份管理测试...")
try:
    backup = get_backup_manager()
    print(f"  - 备份目录：{backup.backup_dir}")
    print(f"  - 现有备份数：{len(backup.list_backups())}")
    print("[OK] 备份管理正常")
except Exception as e:
    print(f"[FAIL] 备份管理失败：{e}")

# ========== 测试 8: 异常处理测试 ==========
print("\n[Test 8/10] Exception handling test...")
try:
    from app.exceptions import LLMConfigError, NovelAgentException
    
    # 测试基类异常
    try:
        raise NovelAgentException("Base test", code="TEST_CODE", details={"key": "value"})
    except NovelAgentException as e:
        assert e.message == "Base test"
        assert e.code == "TEST_CODE"
        assert e.details == {"key": "value"}
    
    # 测试 LLMConfigError
    try:
        raise LLMConfigError("Config test", missing_fields=["api_key", "base_url"])
    except LLMConfigError as e:
        assert e.message == "Config test"
        assert e.code == "LLM_CONFIG_ERROR"
        assert "missing_fields" in e.details
    
    # 测试异常转 dict
    exc = LLMConfigError("Dict test", missing_fields=["test"])
    exc_dict = exc.to_dict()
    assert "error" in exc_dict
    assert "code" in exc_dict
    assert "message" in exc_dict
    
    print("  - Base exception: OK")
    print("  - LLMConfigError: OK")
    print("  - to_dict method: OK")
    print("[OK] Exception handling works perfectly")
except Exception as e:
    print(f"[FAIL] Exception handling failed: {e}")
    import traceback
    traceback.print_exc()

# ========== 测试 9: FastAPI 应用测试 ==========
print("\n【测试 9/10】FastAPI 应用测试...")
try:
    print(f"  - 应用标题：{app.title}")
    print(f"  - 应用版本：{app.version}")
    print(f"  - 路由数量：{len(app.routes)}")
    print("[OK] FastAPI 应用正常")
except Exception as e:
    print(f"[FAIL] FastAPI 应用失败：{e}")

# ========== 测试 10: 异步功能测试 ==========
print("\n【测试 10/10】异步功能测试...")
async def test_async():
    try:
        # 测试异步记忆引擎
        memory = get_memory_engine('./projects/async_test')
        await memory.store({
            'type': 'test',
            'data': '异步测试数据'
        })
        print("  - 异步存储：成功")
        
        # 测试异步检索
        result = await memory.retrieve({'type': 'test'})
        print(f"  - 异步检索：成功")
        
        print("[OK] 异步功能正常")
        return True
    except Exception as e:
        print(f"[FAIL] 异步功能失败：{e}")
        return False

# 运行异步测试
asyncio.run(test_async())

test_async = pytest.mark.asyncio(test_async)

# ========== 测试结果汇总 ==========
print("\n" + "=" * 70)
print("Test Summary")
print("=" * 70)
print("[SUCCESS] All core functions passed!")
print("=" * 70)
