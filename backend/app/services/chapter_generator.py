# ==========================================
# 多 Agent 协作小说系统 - 分段章节生成器
# 解决AI单次生成字数不足问题
# ==========================================

from typing import List, Dict, Any, Optional
import logging

from app.author_styles import get_author_style, apply_style_strength

logger = logging.getLogger(__name__)


class ChapterGenerator:
    """
    分段章节生成器
    
    核心思路：
    1. 将长章节拆分成3-4个段落
    2. 逐段生成，每段约800字
    3. 段落间自然过渡
    4. 合并成完整章节
    """
    
    def __init__(self, llm_call_func):
        """
        Args:
            llm_call_func: 异步函数，签名 async def(prompt, max_tokens) -> str
        """
        self.llm_call_func = llm_call_func
    
    async def generate_chapter(
        self,
        outline: str,
        word_count_target: int = 2500,
        prev_chapters: List[Dict[str, Any]] = None,
        character_notes: str = "",
        world_map: Optional[Dict] = None,
        style: str = "default",
        style_strength: Optional[str] = None,
        next_chapter_baton: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        生成分段章节
        
        Returns:
            完整章节内容字符串
        """
        style_config = get_author_style(style)
        # Apply user-selected style strength if provided
        if style_strength:
            try:
                style_config = apply_style_strength(style_config, style_strength)
            except Exception:
                # Fallback to without strength if anything goes wrong
                pass
        logger.info(f"[ChapterGenerator] outline length={len(outline)}, character_notes length={len(character_notes)}, has_world_map={bool(world_map)}")

        # 计算分段数：每段约800字
        # 中文 1 字 ≈ 1.5 tokens，需要给 max_tokens 留足余量
        segment_count = max(3, min(5, word_count_target // 700))
        segment_target = word_count_target // segment_count
        
        logger.info(f"分段生成：目标{word_count_target}字，分{segment_count}段，每段约{segment_target}字")
        
        # 生成段落大纲
        segments = await self._generate_segment_outlines(
            outline, segment_count, prev_chapters, character_notes, style_config
        )
        logger.info(f"[ChapterGenerator] generated segment outlines count={len(segments)}")
        
        if not segments or len(segments) < 2:
            # 如果分段失败，回退到单次生成
            logger.warning("分段生成失败，回退到单次生成")
            single_pass = await self._generate_single_pass(outline, word_count_target, prev_chapters, character_notes, world_map, style_config)
            logger.info(f"[ChapterGenerator] single-pass content length={len(single_pass) if single_pass else 0}")
            if len(single_pass.strip()) < max(500, word_count_target // 3):
                raise ValueError(f"single_pass_too_short:{len(single_pass.strip())}")
            return single_pass
        
        # 逐段生成，每段检查长度，不足则补段
        full_content = ""
        failed_segments = 0
        for i, seg_outline in enumerate(segments):
            logger.info(f"生成第{i+1}/{len(segments)}段，目标{segment_target}字")
            seg_content = await self._generate_segment(
                seg_outline,
                segment_target,
                prev_content=full_content,
                character_notes=character_notes,
                world_map=world_map,
                style=style,
                style_config=style_config,
                segment_index=i + 1,
                total_segments=len(segments),
                next_chapter_baton=next_chapter_baton,
                is_last_segment=(i == len(segments) - 1)
            )
            logger.info(f"[ChapterGenerator] segment {i+1} content length={len(seg_content) if seg_content else 0}")
            if seg_content:
                full_content += seg_content + "\n\n"
            else:
                failed_segments += 1

        # 章节总字数硬顶：不超过目标的 120%
        max_acceptable = int(word_count_target * 1.2)
        if len(full_content.strip()) > max_acceptable:
            logger.warning(f"章节总字数 {len(full_content.strip())} 超过上限 {max_acceptable}，截断到合理长度")
            # 在最后一个完整句号处截断
            cutoff = full_content[:max_acceptable]
            last_period = cutoff.rfind('。')
            if last_period > 0:
                full_content = cutoff[:last_period + 1]
            else:
                full_content = cutoff
            logger.info(f"截断后总字数：{len(full_content.strip())}")

        # 如果总字数不足目标的 90%，自动补段直到达标
        min_acceptable = int(word_count_target * 0.9)
        attempts = 0
        while len(full_content.strip()) < min_acceptable and attempts < 3:
            attempts += 1
            remaining = word_count_target - len(full_content.strip())
            logger.info(f"章节总字数 {len(full_content.strip())} 不足目标 {word_count_target}，自动补段（第{attempts}次），需补{remaining}字")
            extra_outline = f"继续推进本章情节，收束已有线索，补充约{remaining}字的内容。注意不要重复已有内容。"
            extra_content = await self._generate_segment(
                extra_outline,
                remaining,
                prev_content=full_content,
                character_notes=character_notes,
                world_map=world_map,
                style=style,
                style_config=style_config,
                segment_index=len(segments) + attempts,
                total_segments=len(segments) + 3
            )
            if extra_content and len(extra_content.strip()) > 100:
                full_content += "\n\n" + extra_content.strip()
                logger.info(f"补段成功，当前总字数：{len(full_content.strip())}")
            else:
                logger.warning(f"补段失败或内容过短，停止补段")
                break

        # 如果最后一段明显不足目标长度，且总字数仍在上限内，尝试重写最后一段
        content_parts = [p for p in full_content.strip().split("\n\n") if p.strip()]
        if content_parts and len(full_content.strip()) < max_acceptable:
            last_part = content_parts[-1]
            if len(last_part.strip()) < segment_target * 0.6:
                logger.warning(f"最后一段长度不足：目标约{segment_target}字，实际{len(last_part.strip())}字，尝试重写最后一段")
                last_outline = segments[-1] if segments else outline
                rewritten_last = await self._generate_segment(
                    last_outline,
                    segment_target,
                    prev_content="\n\n".join(content_parts[:-1]),
                    character_notes=character_notes,
                    world_map=world_map,
                    style=style,
                    style_config=style_config,
                    segment_index=len(content_parts),
                    total_segments=max(len(segments), len(content_parts))
                )
                if rewritten_last and len(rewritten_last.strip()) > len(last_part.strip()):
                    content_parts[-1] = rewritten_last.strip()
                    full_content = "\n\n".join(content_parts) + "\n\n"
                    logger.info(f"最后一段重写成功，新长度：{len(rewritten_last.strip())}")

        if len(full_content.strip()) < max(800, int(word_count_target * 0.6)) or failed_segments == len(segments):
            logger.warning("分段正文生成结果不足，回退到单次生成")
            single_pass = await self._generate_single_pass(outline, word_count_target, prev_chapters, character_notes, world_map, style_config)
            logger.info(f"[ChapterGenerator] single-pass content length={len(single_pass) if single_pass else 0}")
            if len(single_pass.strip()) < max(800, int(word_count_target * 0.6)):
                raise ValueError(
                    f"chapter_generation_failed:segments={len(segments)},failed_segments={failed_segments},segment_content_len={len(full_content.strip())},single_pass_len={len(single_pass.strip())}"
                )
            return single_pass
         
        logger.info(f"分段生成完成，总字数：{len(full_content)}")
        return full_content.strip()
    
    async def _generate_segment_outlines(
        self,
        outline: str,
        count: int,
        prev_chapters: List[Dict[str, Any]] = None,
        character_notes: str = "",
        style_config: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """生成段落级大纲"""
        style_config = style_config or get_author_style("default")
        prev_context = ""
        if prev_chapters:
            recent = prev_chapters[-2:] if len(prev_chapters) >= 2 else prev_chapters
            prev_context = "\n".join([
                f"第{c['chapter_num']}章摘要：{c.get('content', '')[:200]}"
                for c in recent
            ])
        
        style_rules = "\n".join([f"- {item}" for item in style_config.get("guidelines", [])[:4]])
        style_forbidden = "\n".join([f"- {item}" for item in style_config.get("forbidden", [])[:3]])
        prompt = f"""作为专业小说编辑，请将以下章节大纲拆分成{count}个段落大纲：

【章节大纲】
{outline}

【前文摘要】
{prev_context}

【角色备注】
{character_notes}

【写作风格】
风格：{style_config.get('name')}
说明：{style_config.get('description')}
风格强度：{style_config.get('strength', 'medium')}
强度说明：{style_config.get('strength_instruction', '')}
风格要求：
{style_rules}
避免事项：
{style_forbidden}

要求：
1. 每段有明确的小目标
2. 段落间有自然过渡
3. 保持情节连贯
4. 每段约800字的内容量

请输出{count}段大纲，用"---"分隔每段："""

        try:
            result = await self.llm_call_func(prompt, max_tokens=1000)
            logger.info(f"[ChapterGenerator] raw segment-outline response length={len(result) if result else 0}")
            segments = [s.strip() for s in result.split('---') if s.strip()]
            # 确保数量正确
            return segments[:count] if len(segments) >= count else segments
        except Exception as e:
            logger.error(f"生成段落大纲失败：{e}")
            return []
    
    async def _generate_segment(
        self,
        segment_outline: str,
        target_words: int,
        prev_content: str = "",
        character_notes: str = "",
        world_map: Optional[Dict] = None,
        style: str = "default",
        style_config: Optional[Dict[str, Any]] = None,
        segment_index: int = 1,
        total_segments: int = 3,
        next_chapter_baton: Optional[Dict[str, Any]] = None,
        is_last_segment: bool = False
    ) -> str:
        """生成单个段落"""
        style_config = style_config or get_author_style(style)
        # 取前文最后300字作为衔接
        prev_snippet = ""
        if prev_content:
            prev_snippet = prev_content[-300:]
        
        world_context = ""
        if world_map:
            world_context = f"\n【世界观设定】{str(world_map)[:500]}"
        
        # 根据段落位置调整提示
        position_hint = ""
        if segment_index == 1:
            position_hint = "这是章节开头，需要引入场景和人物，建立氛围。注意与前文衔接，但不要重复前文已写过的内容。"
        elif segment_index == total_segments:
            position_hint = "这是章节结尾，需要收束本段情节，并留下悬念吸引读者继续阅读下一章。"
        else:
            position_hint = "这是章节中间部分，需要推进情节，发展冲突。确保情节向前推进，不要停留在原地。"
        
        # 下一章交接棒约束
        baton_hint = ""
        if next_chapter_baton:
            if is_last_segment:
                baton_parts = []
                if next_chapter_baton.get('must_continue_from'):
                    baton_parts.append(f"本章结尾需要为以下状态留出接口：{next_chapter_baton['must_continue_from']}")
                if next_chapter_baton.get('carry_forward_emotion'):
                    baton_parts.append(f"结尾情绪应该：{next_chapter_baton['carry_forward_emotion']}")
                if next_chapter_baton.get('carry_forward_hooks'):
                    baton_parts.append(f"需要继续推进的伏笔：{'、'.join(next_chapter_baton['carry_forward_hooks'])}")
                if next_chapter_baton.get('forbidden_backtracks'):
                    baton_parts.append(f"禁止回头重写：{'、'.join(next_chapter_baton['forbidden_backtracks'])}")
                if baton_parts:
                    baton_hint = "\n【下一章接口约束】\n" + "\n".join(baton_parts)
            else:
                if next_chapter_baton.get('forbidden_backtracks'):
                    baton_hint = f"\n【禁止事项】\n禁止回头重写：{'、'.join(next_chapter_baton['forbidden_backtracks'])}"
        
        style_rules = "\n".join([f"- {item}" for item in style_config.get("guidelines", [])[:5]])
        style_forbidden = "\n".join([f"- {item}" for item in style_config.get("forbidden", [])[:3]])
        style_features = "、".join(style_config.get("features", []))
        style_example = (style_config.get("tone_examples") or [""])[0]

        prompt = f"""你是一位专业的小说写手，请严格按照指定作家风格创作段落正文：

【本段任务】
{segment_outline}

{position_hint}
{baton_hint}

【前文衔接】（请保持连贯，不要重复前文内容）
{prev_snippet}

【重要提醒】
- 前文衔接只用于了解上下文，绝对不能重复写前文已经发生过的情节
- 必须创作新的情节，推进故事发展

【角色备注】
{character_notes}
{world_context}

【指定作家风格】
风格名称：{style_config.get('name')}
风格说明：{style_config.get('description')}
风格强度：{style_config.get('strength', 'medium')}
强度说明：{style_config.get('strength_instruction', '')}
核心特征：{style_features}
写作守则：
{style_rules}
避免事项：
{style_forbidden}
语感参考：{style_example}

【要求】
1. 字数：约{target_words}字（不少于{target_words - 100}字）
2. 第三人称叙述
3. 包含环境描写、心理描写、对话
4. 节奏紧凑，有悬念
5. 符合网文风格
6. 与前文自然衔接
7. 不要出现"本章"、"本节"等元叙述
8. 不要重复前文内容

请开始创作正文："""

        try:
            # 中文 1 字 ≈ 1.5-2 tokens，给 max_tokens 留足余量避免截断
            # 同时考虑 prompt 本身也占用 tokens，需要更大的预算
            content = await self.llm_call_func(prompt, max_tokens=int(target_words * 2))
            logger.info(f"[ChapterGenerator] raw segment {segment_index} response length={len(content) if content else 0}")
            llm_meta = getattr(getattr(self.llm_call_func, '__self__', None), 'last_llm_meta', None)
            if llm_meta:
                logger.info(f"[ChapterGenerator] segment {segment_index} llm_meta: finish_reason={llm_meta.get('finish_reason')}, requested_max_tokens={llm_meta.get('requested_max_tokens')}, prompt_tokens={llm_meta.get('prompt_tokens')}, completion_tokens={llm_meta.get('completion_tokens')}")
            
            # 如果返回内容明显不足目标，记录警告
            if content and len(content.strip()) < target_words * 0.5:
                logger.warning(f"Segment {segment_index} 产出不足：目标{target_words}字，实际{len(content.strip())}字")
            
            return content.strip()
        except Exception as e:
            logger.error(f"生成段落失败（第{segment_index}段）：{e}")
            return ""
    
    async def _generate_single_pass(
        self,
        outline: str,
        word_count_target: int,
        prev_chapters: List[Dict[str, Any]] = None,
        character_notes: str = "",
        world_map: Optional[Dict] = None,
        style_config: Optional[Dict[str, Any]] = None,
    ) -> str:
        """回退方案：单次生成"""
        style_config = style_config or get_author_style("default")
        prev_snippet = ""
        if prev_chapters:
            prev_snippet = prev_chapters[-1].get('content', '')[-300:] if prev_chapters else ""
        
        style_rules = "\n".join([f"- {item}" for item in style_config.get("guidelines", [])[:5]])
        style_forbidden = "\n".join([f"- {item}" for item in style_config.get("forbidden", [])[:3]])
        style_features = "、".join(style_config.get("features", []))
        style_example = (style_config.get("tone_examples") or [""])[0]

        prompt = f"""你是一位专业的小说写手，请严格按照指定作家风格创作章节正文：

【章节大纲】
{outline}

【前文衔接】
{prev_snippet}

【重要提醒】
- 前文衔接只用于了解上下文，绝对不能重复写前文已经发生过的情节
- 必须创作新的情节，推进故事发展

【角色备注】
{character_notes}

【指定作家风格】
风格名称：{style_config.get('name')}
风格说明：{style_config.get('description')}
风格强度：{style_config.get('strength', 'medium')}
强度说明：{style_config.get('strength_instruction', '')}
核心特征：{style_features}
写作守则：
{style_rules}
避免事项：
{style_forbidden}
语感参考：{style_example}

【要求】
1. 字数：约{word_count_target}字
2. 第三人称叙述
3. 包含环境描写、心理描写、对话
4. 节奏紧凑，有悬念
5. 符合网文风格

请开始创作正文："""

        try:
            # 中文 1 字 ≈ 1.5-2 tokens，给 max_tokens 留足余量避免截断
            content = await self.llm_call_func(prompt, max_tokens=int(word_count_target * 2))
            logger.info(f"[ChapterGenerator] raw single-pass response length={len(content) if content else 0}")
            llm_meta = getattr(getattr(self.llm_call_func, '__self__', None), 'last_llm_meta', None)
            if llm_meta:
                logger.info(f"[ChapterGenerator] single-pass llm_meta: finish_reason={llm_meta.get('finish_reason')}, requested_max_tokens={llm_meta.get('requested_max_tokens')}, prompt_tokens={llm_meta.get('prompt_tokens')}, completion_tokens={llm_meta.get('completion_tokens')}")
            return (content or "").strip()
        except Exception as e:
            logger.error(f"单次生成失败：{e}")
            return ""
