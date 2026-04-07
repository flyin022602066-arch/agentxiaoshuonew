# ==========================================
# 多 Agent 协作小说系统 - 基础框架测试
# ==========================================
"""
测试阶段 1 基础框架是否正常工作
"""

import asyncio
import sys
from pathlib import Path

import pytest

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent / "backend"))

pytestmark = pytest.mark.asyncio


async def test_config():
    """测试配置管理"""
    print("\n=== 测试配置管理 ===")
    
    try:
        from app.config import get_config_manager
        
        config = get_config_manager()
        print(f"✓ 配置管理器初始化成功")
        print(f"  项目名：{config.app_config.project_name if config.app_config else 'N/A'}")
        print(f"  默认提供商：{config.get_default_provider()}")
        print(f"  已配置提供商：{config.get_all_providers()}")
        
        return True
    except Exception as e:
        print(f"✗ 配置管理测试失败：{e}")
        return False


async def test_llm_client():
    """测试 LLM 客户端"""
    print("\n=== 测试 LLM 客户端 ===")
    
    try:
        from app.utils.llm_client import get_llm_client
        
        client = get_llm_client()
        print(f"✓ LLM 客户端初始化成功")
        print(f"  配置文件：{client.config_path}")
        print(f"  提供商数量：{len(client.providers)}")
        
        # 测试配置验证
        if client.providers:
            provider_name = list(client.providers.keys())[0]
            validation = client.validate_provider(provider_name)
            print(f"  配置验证 ({provider_name}): {validation}")
        
        return True
    except Exception as e:
        print(f"✗ LLM 客户端测试失败：{e}")
        return False


async def test_agent_registry():
    """测试 Agent 注册表"""
    print("\n=== 测试 Agent 注册表 ===")
    
    try:
        from app.agents.registry import AgentRegistry, register_agent
        from app.agents import BaseAgent
        
        registry = AgentRegistry()
        print(f"✓ Agent 注册表初始化成功")
        
        # 测试注册
        class TestAgent(BaseAgent):
            async def execute(self, task):
                return {"status": "ok"}
            
            def get_system_prompt(self):
                return "Test prompt"
        
        test_agent = TestAgent("test_agent", {})
        register_agent(test_agent)
        
        print(f"  已注册 Agent: {list(registry.get_all().keys())}")
        print(f"  Agent 状态：{registry.get_status()}")
        
        return True
    except Exception as e:
        print(f"✗ Agent 注册表测试失败：{e}")
        return False


async def test_health_check():
    """测试健康检查端点"""
    print("\n=== 测试健康检查 ===")
    
    try:
        from app.api.health import health_check
        
        result = await health_check(detailed=False)
        print(f"✓ 健康检查执行成功")
        print(f"  状态：{result.get('status')}")
        print(f"  检查项：{list(result.get('checks', {}).keys())}")
        
        return True
    except Exception as e:
        print(f"✗ 健康检查测试失败：{e}")
        return False


async def test_backup_manager():
    """测试备份管理"""
    print("\n=== 测试备份管理 ===")
    
    try:
        from app.storage.backup import BackupManager
        
        manager = BackupManager()
        print(f"✓ 备份管理器初始化成功")
        print(f"  备份目录：{manager.backup_dir}")
        print(f"  现有备份数：{len(manager.list_backups())}")
        
        return True
    except Exception as e:
        print(f"✗ 备份管理测试失败：{e}")
        return False


async def main():
    """运行所有测试"""
    print("=" * 60)
    print("多 Agent 协作小说系统 - 阶段 1 基础框架测试")
    print("=" * 60)
    
    tests = [
        ("配置管理", test_config),
        ("LLM 客户端", test_llm_client),
        ("Agent 注册表", test_agent_registry),
        ("健康检查", test_health_check),
        ("备份管理", test_backup_manager),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = await test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n✗ {name} 测试异常：{e}")
            results.append((name, False))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"  {status} - {name}")
    
    print(f"\n总计：{passed}/{total} 通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！阶段 1 基础框架正常。")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 个测试失败，请检查。")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
