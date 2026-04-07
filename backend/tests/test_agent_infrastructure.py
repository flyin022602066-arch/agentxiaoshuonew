import json
import pytest


@pytest.mark.asyncio
async def test_base_agent_injects_dependencies_and_calls_llm():
    from app.agents.base_agent import BaseAgent

    class DemoAgent(BaseAgent):
        def get_system_prompt(self):
            return "demo-system"

        async def execute(self, task):
            return await self.call_llm("hello", temperature=0.2, max_tokens=123)

    class StubLLM:
        def __init__(self):
            self.calls = []

        async def generate(self, prompt, system_prompt, **kwargs):
            self.calls.append({"prompt": prompt, "system_prompt": system_prompt, "kwargs": kwargs})
            return "demo-result"

    llm = StubLLM()
    memory = object()
    agent = DemoAgent("demo_agent", {"llm_client": llm, "memory_engine": memory})

    result = await agent.execute({})

    assert result == "demo-result"
    assert agent.llm_client is llm
    assert agent.memory_engine is memory
    assert llm.calls[0]["system_prompt"] == "demo-system"
    assert llm.calls[0]["kwargs"]["max_tokens"] == 123


@pytest.mark.asyncio
async def test_memory_engine_style_storage_supports_techniques(tmp_path):
    from app.memory.memory_engine import MemoryEngine

    engine = MemoryEngine(str(tmp_path))
    await engine.long_term.store_technique({"name": "伏笔千里", "description": "提前埋设关键信息"})

    styles_path = tmp_path / "memory" / "styles.json"
    payload = json.loads(styles_path.read_text(encoding="utf-8"))

    assert isinstance(payload, dict)
    assert payload["techniques"][0]["name"] == "伏笔千里"


@pytest.mark.asyncio
async def test_memory_engine_apply_technique_returns_matching_description(tmp_path):
    from app.memory.memory_engine import MemoryEngine

    engine = MemoryEngine(str(tmp_path))
    await engine.long_term.store_technique(
        {"id": "foreshadowing", "name": "伏笔千里", "description": "在当前场景埋下后文回收的关键信息。"}
    )

    result = await engine.apply_technique("foreshadowing", {"scene_type": "opening"})

    assert "伏笔千里" in result
    assert "关键信息" in result


def test_agent_execute_task_awaits_async_agent(monkeypatch):
    from app.tasks.agent_tasks import agent_execute_task
    import app.agents.registry as registry_module

    class StubAgent:
        async def execute(self, task):
            return {"status": "ok", "echo": task["value"]}

    monkeypatch.setattr(registry_module, "get_agent", lambda agent_id: StubAgent())

    result = agent_execute_task.run("writer_agent", {"value": 42})

    assert result["status"] == "success"
    assert result["result"]["echo"] == 42
