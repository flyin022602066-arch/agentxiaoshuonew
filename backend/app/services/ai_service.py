from typing import Any, Dict


class AIService:
    def list_templates(self):
        from app.templates import list_templates as list_template_defs

        return list_template_defs()

    async def generate_outline(self, data: Dict[str, Any]):
        from app.workflow_executor import get_workflow_executor

        title = data.get("title", "")
        if not title:
            raise ValueError("小说标题不能为空")
        executor = get_workflow_executor()
        return await executor.generate_novel_outline(
            title,
            data.get("genre", ""),
            data.get("description", ""),
            data.get("template_id", "qichengzhuanhe"),
        )

    async def generate_characters(self, data: Dict[str, Any]):
        from app.workflow_executor import get_workflow_executor

        executor = get_workflow_executor()
        return await executor.generate_characters(
            data.get("title", ""),
            data.get("genre", ""),
            data.get("outline", ""),
            data.get("count", 5),
        )

    async def generate_chapter_outline(self, data: Dict[str, Any]):
        from app.workflow_executor import get_workflow_executor

        executor = get_workflow_executor()
        return await executor.generate_chapter_outline(
            data.get("novel_title", ""),
            data.get("chapter_num", 1),
            data.get("overall_outline", ""),
            data.get("context", {}),
            next_chapter_baton=data.get("next_chapter_baton"),
        )

    async def generate_plot(self, data: Dict[str, Any]):
        from app.workflow_executor import get_workflow_executor

        executor = get_workflow_executor()
        return await executor.generate_plot_design(data.get("outline", ""), data.get("characters", []))

    async def generate_style_preview(self, data: Dict[str, Any]):
        from app.author_styles import apply_style_strength, get_author_style
        from app.workflow_executor import get_workflow_executor

        style_id = data.get("style_id", "default")
        strength = data.get("strength", "medium")
        prompt_seed = data.get("prompt_seed") or "少年在雨夜独自踏上修炼之路，前方危机四伏。"
        style = apply_style_strength(get_author_style(style_id), strength)
        executor = get_workflow_executor()

        if not executor.llm_client:
            raise ValueError("LLM 未配置，无法进行风格试写")

        guidelines = "\n".join([f"- {item}" for item in style.get("guidelines", [])[:5]])
        forbidden = "\n".join([f"- {item}" for item in style.get("forbidden", [])[:3]])
        features = "、".join(style.get("features", []))
        example = (style.get("tone_examples") or [""])[0]

        prompt = f"""请根据以下测试设定，生成一段 200-300 字的风格试写文本。

【测试设定】
{prompt_seed}

【作家风格】
风格名称：{style.get('name')}
风格说明：{style.get('description')}
风格强度：{style.get('strength')}
强度说明：{style.get('strength_instruction')}
核心特征：{features}
写作守则：
{guidelines}
避免事项：
{forbidden}
语感参考：{example}

要求：
1. 只输出试写正文，不要解释
2. 体现该风格核心语感
3. 不要照抄语感参考
4. 保持中文自然流畅
"""

        content = await executor._call_llm(prompt, max_tokens=500)
        return {
            "style_id": style_id,
            "style_name": style.get("name"),
            "strength": strength,
            "prompt_seed": prompt_seed,
            "preview": content.strip(),
        }


_ai_service: AIService | None = None


def get_ai_service() -> AIService:
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service
