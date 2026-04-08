# ==========================================
# 多 Agent 协作小说系统 - 真实写作工作流
# 直接调用 LLM 实现 AI 创作
# ==========================================

from typing import Dict, Any, List, Optional
from datetime import datetime
import logging
import httpx
import json
import asyncio
import re
from difflib import SequenceMatcher
from app.agents.registry import get_all_agents, create_agents
from app.author_styles import get_author_style, apply_style_strength
from app.schemas.agent_packets import ChapterPlan, NextChapterBaton

logger = logging.getLogger(__name__)

DEFAULT_DIALOGUE_POLISH_TIMEOUT = 180.0


def _stringify_exception(error: Exception) -> str:
    message = str(error).strip()
    return message or error.__class__.__name__


def _truncate_text(text: str, max_chars: int) -> str:
    text = (text or "").strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "..."


def _normalize_similarity_text(text: str, max_chars: int = 1800) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    collapsed = "".join(text.split())
    return collapsed[:max_chars]


def _extract_carryover_signals(prev_chapter: Dict[str, Any]) -> List[str]:
    signals: List[str] = []
    if not prev_chapter:
        return signals

    baton = prev_chapter.get('next_chapter_baton') or {}
    must_continue_from = (baton.get('must_continue_from') or '').strip()
    carry_forward_emotion = (baton.get('carry_forward_emotion') or '').strip()
    carry_forward_hooks = baton.get('carry_forward_hooks') or []

    for text in [must_continue_from, carry_forward_emotion, *carry_forward_hooks]:
        normalized = (text or '').strip()
        if normalized:
            signals.append(normalized[:24])

    content = (prev_chapter.get('content') or '').strip()
    if content:
        tail = content[-120:]
        sentences = [segment.strip() for segment in tail.replace('！', '。').replace('？', '。').replace('……', '。').split('。') if segment.strip()]
        if sentences:
            signals.append(sentences[-1][:24])

    deduped: List[str] = []
    for signal in signals:
        if signal and signal not in deduped:
            deduped.append(signal)
    return deduped


def _should_trigger_de_ai(ai_patterns: List[str], content: str) -> bool:
    if not ai_patterns:
        return False

    severe_markers = [
        '眼中闪过一丝', '嘴角勾起一抹', '深吸一口气', '心中暗道',
        '命运的齿轮', '风暴酝酿', '值得注意的是', '由此可见',
    ]
    severe_hits = sum(1 for pattern in ai_patterns if any(marker in pattern for marker in severe_markers))
    if severe_hits >= 2:
        return True

    density = len(ai_patterns)
    if density >= 3:
        return True

    normalized_length = max(len((content or '').strip()), 1)
    return density >= 2 and normalized_length < 1200


def scan_publishability_risks(content: str) -> Dict[str, Any]:
    text = (content or '').strip()
    if not text:
        return {'blocked': False, 'hits': []}

    rules = [
        ('explicit_sexual', [r'探进衣服', r'按在墙上', r'粗暴', r'按住.*?身体']),
        ('graphic_violence', [r'划开皮肉', r'碎肉', r'骨头都翻', r'血.*?溅']),
        ('drug_abuse', [r'点燃粉末', r'吸了下去', r'药劲', r'兴奋得发抖']),
    ]

    hits: List[Dict[str, str]] = []
    for category, patterns in rules:
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                hits.append({
                    'category': category,
                    'pattern': pattern,
                    'excerpt': text[max(0, match.start() - 10): match.end() + 10],
                })
                break

    return {
        'blocked': bool(hits),
        'hits': hits,
    }


def evaluate_fanqie_feel(content: str) -> Dict[str, Any]:
    text = (content or '').strip()
    if not text:
        return {'pass': False, 'score': 0, 'issues': [{'type': 'empty', 'message': '内容为空'}]}

    issues: List[Dict[str, str]] = []
    score = 100

    opening = text[:260]
    opening_event_markers = ['刚', '忽然', '突然', '立刻', '当场', '下一秒', '脚步', '名字', '危险', '追兵', '亮起了灯']
    if not any(marker in opening for marker in opening_event_markers):
        issues.append({'type': 'opening_speed', 'message': '开头进入事件过慢，缺少即时冲突或异变。'})
        score -= 25

    middle = text[len(text)//3: len(text)*2//3] if len(text) > 90 else text
    progression_markers = ['却', '但', '忽然', '然而', '立刻', '转身', '冲', '追', '拦', '发现', '没想到', '脚步声', '没有退路', '抢先', '门口', '后窗']
    progression_hits = sum(1 for marker in progression_markers if marker in middle)
    if progression_hits < 2:
        issues.append({'type': 'progression_density', 'message': '中段推进密度不足，解释或停顿偏多。'})
        score -= 20

    conflict_markers = ['冲突', '危险', '追兵', '威胁', '反击', '拦住', '逼近', '杀意', '质问', '翻脸', '没有退路', '人质', '冷声', '脚步声', '抢先', '对峙', '追杀', '堵死', '按住']
    if not any(marker in text for marker in conflict_markers):
        issues.append({'type': 'conflict_presence', 'message': '正文缺少明确冲突或转折。'})
        score -= 20

    tail = text[-220:]
    hook_markers = ['你终于来了', '谁在', '到底是谁', '没有退路', '下一章', '真正的麻烦', '他愣住了', '门外又响起脚步声', '可他不知道', '东西已经在你屋里了', '第二轮追杀', '堵死在屋里']
    if not any(marker in tail for marker in hook_markers):
        issues.append({'type': 'hook_strength', 'message': '章末钩子偏弱，追读拉力不足。'})
        score -= 25

    return {
        'pass': score >= 60 and not issues,
        'score': max(score, 0),
        'issues': issues,
    }


def evaluate_qimao_feel(content: str) -> Dict[str, Any]:
    text = (content or '').strip()
    if not text:
        return {'pass': False, 'score': 0, 'issues': [{'type': 'empty', 'message': '内容为空'}]}

    issues: List[Dict[str, str]] = []
    score = 100

    emotion_markers = ['心里', '心头', '微微', '顿了一下', '沉了一下', '发紧', '迟疑', '低声', '没有立刻', '想起']
    emotion_hits = sum(1 for marker in emotion_markers if marker in text)
    if emotion_hits < 2:
        issues.append({'type': 'emotion_continuity', 'message': '情绪推进偏薄，人物内心与情绪转折不足。'})
        score -= 25

    texture_markers = ['药味', '夜风', '窗边', '灯火', '雨声', '栀子花', '指节', '衣角', '茶盏', '光影', '凉意', '潮气']
    texture_hits = sum(1 for marker in texture_markers if marker in text)
    if texture_hits < 2:
        issues.append({'type': 'scene_texture', 'message': '场景质感偏薄，环境与感官细节不足。'})
        score -= 25

    interaction_markers = ['看了他一眼', '把茶盏推', '没有接话', '低声问', '沉默了几息', '手指', '目光', '呼吸', '微微顿了一下', '谁都没有先提', '像是怕她', '本想直接问出口']
    interaction_hits = sum(1 for marker in interaction_markers if marker in text)
    if interaction_hits < 2:
        issues.append({'type': 'interaction_layering', 'message': '人物互动层次不足，缺少动作、停顿与潜台词。'})
        score -= 20

    tail = text[-220:]
    harsh_hook_markers = ['你终于来了', '第二轮追杀', '堵死', '没有退路', '门外已经有人']
    soft_pull_markers = ['你是不是一直在怪我', '她没有立刻回答', '可她终究没有问出口', '他却没有再解释', '那句话到底还是留在了心里', '没有把那句', '没有说出口', '终究还是没有', '垂下眼']
    if any(marker in tail for marker in harsh_hook_markers):
        issues.append({'type': 'hook_harshness', 'message': '章末拉力过硬，更接近番茄感而非七猫感。'})
        score -= 15
    elif not any(marker in tail for marker in soft_pull_markers):
        issues.append({'type': 'hook_softness', 'message': '章末拉力不足，缺少七猫式柔性牵引。'})
        score -= 15

    return {
        'pass': score >= 60 and not issues,
        'score': max(score, 0),
        'issues': issues,
    }


def _split_publishability_hits(hits: List[Dict[str, str]]) -> Dict[str, List[Dict[str, str]]]:
    repairable_categories = {'explicit_sexual', 'drug_abuse'}
    repairable = [hit for hit in hits if hit.get('category') in repairable_categories]
    unrepairable = [hit for hit in hits if hit.get('category') not in repairable_categories]
    return {
        'repairable': repairable,
        'unrepairable': unrepairable,
    }


def _check_style_drift(check_result: Dict[str, Any], min_score: int = 50) -> Optional[Dict[str, Any]]:
    style_feedback = (check_result or {}).get('style_feedback') or {}
    score = style_feedback.get('score')
    if score is None:
        return None
    if score >= min_score:
        return None

    return {
        'score': score,
        'style_id': style_feedback.get('style_id'),
        'summary': style_feedback.get('summary', ''),
        'missing_features': style_feedback.get('missing_features', []) or [],
    }


def _check_chapter_carryover(content: str, prev_chapters: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not content or not prev_chapters:
        return None

    latest = prev_chapters[-1] or {}
    opening_window = (content or '').strip()[:260]
    if not opening_window:
        return None

    signals = _extract_carryover_signals(latest)
    if not signals:
        return None

    matched = [signal for signal in signals if signal and signal in opening_window]
    if matched:
        return None

    return {
        'previous_chapter_num': latest.get('chapter_num'),
        'signals': signals[:3],
    }


def _extract_outline_summary(outline_text: str) -> str:
    text = (outline_text or "").strip()
    if not text:
        return ""

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        normalized = line.replace("：", ":")
        if normalized.startswith("核心事件:"):
            return normalized.split(":", 1)[1].strip()

    first_nonempty = next((line.strip() for line in text.splitlines() if line.strip()), "")
    return first_nonempty[:120]


def check_ending_completeness(content: str) -> Dict[str, Any]:
    """检查章节结尾是否完整。"""
    text = (content or '').strip()
    if not text:
        return {
            'is_complete': False,
            'reason': '正文为空',
        }

    # 取最后 150 字
    tail = text[-150:]
    normalized_tail = tail.replace('！', '。').replace('？', '。').replace('……', '。')
    tail_sentences = [segment.strip() for segment in normalized_tail.split('。') if segment.strip()]
    last_sentence = tail_sentences[-1] if tail_sentences else ""

    # 如果最后一句很短，说明可能以标点正常收束了
    if len(last_sentence) < 3:
        return {
            'is_complete': True,
            'reason': '',
        }

    # 悬空结构检测
    dangling_prefixes = [
        '一人', '他正', '她正', '正要', '忽然', '突然', '然而', '却',
        '只见', '只见那', '却说', '但见', '谁知', '没想到', '没想到',
        '刚', '才刚', '眼看', '正当', '就在', '此时', '这时', '那',
        '这', '一个', '两个', '三名', '四名',
    ]

    transition_markers = [
        '下一秒', '下一刻', '紧接着', '转眼间', '就在这时', '就在此时', '与此同时',
        '下一瞬', '下一息', '下一刹',
    ]

    closure_markers = [
        '他知道', '她知道', '他明白', '她明白', '他意识到', '她意识到', '他终于', '她终于',
        '这一夜', '这一刻', '今夜之后', '这一章', '夜色更深', '风又起了', '答案还没来',
        '但他没有回头', '但她没有回头', '故事才刚开始', '真正的麻烦',
    ]

    for prefix in dangling_prefixes:
        if last_sentence.startswith(prefix) and len(last_sentence) < 20:
            return {
                'is_complete': False,
                'reason': f'结尾停在悬空结构"{prefix}"上，句子未收束',
            }

    if tail_sentences:
        last_full_sentence = tail_sentences[-1]
        has_transition_marker = any(marker in last_full_sentence for marker in transition_markers)
        has_closure_marker = any(marker in last_full_sentence for marker in closure_markers)
        if has_transition_marker and not has_closure_marker:
            return {
                'is_complete': False,
                'reason': '结尾停在过渡推进节点，只完成了下一步铺垫，缺少本章收束',
            }

    # 检查是否以正常标点结尾
    proper_endings = ['。', '！', '？', '……', '"', '"', '」', '』', '—']
    if any(text.endswith(e) for e in proper_endings):
        return {
            'is_complete': True,
            'reason': '',
        }

    # 如果最后 150 字没有句号/问号/叹号，很可能没收束
    if '。' not in tail and '！' not in tail and '？' not in tail and '……' not in tail:
        return {
            'is_complete': False,
            'reason': '结尾段落缺少正常收束标点',
        }

    return {
        'is_complete': True,
        'reason': '',
    }


def evaluate_style_hit(content: str, style_id: str, style_strength: Optional[str] = None) -> Dict[str, Any]:
    style = apply_style_strength(get_author_style(style_id), style_strength or 'medium')
    normalized = (content or '').strip()
    if not normalized:
        return {
            'style_id': style_id,
            'style_name': style.get('name'),
            'score': 0,
            'matched_features': [],
            'missing_features': style.get('features', []),
            'summary': '正文为空，无法判断风格命中情况。',
        }

    score = 35
    matched_features: List[str] = []
    missing_features: List[str] = []
    text = normalized.replace('。', '').replace('，', '')

    feature_keywords = {
        '语言凝练': ['冷', '刀', '灯', '短句'],
        '气质冷峻': ['冷', '寒', '霜', '夜'],
        '戏剧感强': ['忽然', '骤然', '一瞬', '对峙'],
        '留白锋利': ['沉默', '没有回答', '未说完', '停住'],
        '人物立体': ['目光', '神情', '心里', '旧事'],
        '江湖氛围': ['江湖', '长街', '门派', '风铃'],
        '叙事稳健': ['随后', '紧接着', '片刻后'],
        '门派体系': ['门派', '弟子', '掌门', '师门'],
    }

    for feature in style.get('features', []):
        keywords = feature_keywords.get(feature, [feature[:2]])
        if any(keyword and keyword in text for keyword in keywords):
            matched_features.append(feature)
            score += 12
        else:
            missing_features.append(feature)

    if style.get('tone_examples'):
        example = style['tone_examples'][0]
        if any(token and token in normalized for token in [example[:2], example[:3], '冷', '夜', '风']):
            score += 8

    score = max(0, min(100, score))
    if score >= 80:
        summary = f"风格命中较强，{style.get('name')}的核心特征已有明显体现。"
    elif score >= 60:
        summary = f"风格命中中等，{style.get('name')}已有可辨识气质，但仍可继续强化。"
    else:
        summary = f"风格命中偏弱，当前文本还没有充分体现{style.get('name')}的代表性语感。"

    return {
        'style_id': style_id,
        'style_name': style.get('name'),
        'score': score,
        'matched_features': matched_features,
        'missing_features': missing_features,
        'summary': summary,
    }


def build_chapter_plan(chapter_num: int, outline: str, prev_chapters: List[Dict[str, Any]], style_feedback: Optional[Dict[str, Any]] = None) -> ChapterPlan:
    latest_summary = _truncate_text(prev_chapters[-1].get('content', ''), 120) if prev_chapters else '无前章'
    return {
        'chapter_num': chapter_num,
        'chapter_goal': _truncate_text(outline, 120),
        'must_advance': [f'承接并推进第{chapter_num}章主线'],
        'must_not_repeat': ['禁止重复上一章已经完整发生的主事件'],
        'scene_progression': ['承接上一章结尾', '推进当前冲突', '形成新的章节收束'],
        'hook_actions': [],
        'ending_state': {
            'plot_state': '本章事件应完成一个清晰的局部收束，不能只停留在推进前一刻',
            'emotion_state': '保持连续的情绪推进',
            'hook': '在局部收束后，为下一章留下明确悬念与接续点'
        },
        'chapter_memory_point': latest_summary,
        'style_focus': style_feedback.get('matched_features', [])[:3] if style_feedback else []
    }


def build_next_chapter_baton(outline_summary: str, style_feedback: Optional[Dict[str, Any]] = None) -> NextChapterBaton:
    return {
        'must_continue_from': outline_summary or '延续本章结尾的核心事件',
        'carry_forward_emotion': '延续本章结尾情绪并推进',
        'carry_forward_hooks': ['继续处理本章未解决的悬念'],
        'carry_forward_relationships': [],
        'forbidden_backtracks': ['禁止回头重写上一章已完成主事件']
    }


def evaluate_chapter_completion(content: str, chapter_plan: ChapterPlan, word_count_target: int) -> Dict[str, Any]:
    text = (content or '').strip()
    reasons: List[str] = []
    if len(text) < max(1200, int(word_count_target * 0.7)):
        reasons.append('章节长度明显不足，可能尚未完成本章任务')

    must_advance = chapter_plan.get('must_advance', []) or []
    hit_count = 0
    for item in must_advance:
        key = (item or '')[:8]
        if key and key in text:
            hit_count += 1
    if must_advance and hit_count < max(1, len(must_advance) // 2):
        reasons.append('本章关键推进点命中不足，疑似尚未推进到位')

    ending_state = chapter_plan.get('ending_state', {}) or {}
    plot_state = ending_state.get('plot_state', '')
    if plot_state:
        key = plot_state[:8]
        if key and key not in text[-300:]:
            reasons.append('结尾状态未明显体现，章节可能没有真正写完')

    ending_check = check_ending_completeness(text)
    if not ending_check.get('is_complete', True):
        reasons.append(f"结尾不完整：{ending_check.get('reason', '')}")

    return {
        'is_complete': len(reasons) == 0,
        'reasons': reasons,
    }


class WritingWorkflowExecutor:
    """
    写作工作流执行器
    真实调用 LLM 完成章节创作
    """
    
    def __init__(self, config_service=None):
        self.config_service = config_service
        self.runtime_provider = None
        self.llm_client = None
        self.last_llm_meta = None
        self._load_llm_config()
    
    def _load_llm_config(self):
        """加载 LLM 配置"""
        try:
            if self.config_service is None:
                from app.services.config_service import get_config_service
                self.config_service = get_config_service()

            provider_config = self.config_service.get_active_provider_config()

            if provider_config and provider_config.get('api_key'):
                self.runtime_provider = provider_config
                self.llm_client = {
                    'api_key': provider_config['api_key'],
                    'base_url': provider_config['base_url'],
                    'model': provider_config['model'],
                    'timeout': provider_config.get('timeout', 300)
                }
                logger.info(f"[OK] LLM 配置加载成功：{provider_config['name']}")
                logger.info(f"   Base URL: {provider_config['base_url']}")
            else:
                logger.warning("[FAIL] LLM 配置不完整或未配置默认提供商")
                self.runtime_provider = None
                self.llm_client = None
        except Exception as e:
            logger.error(f"[FAIL] 加载 LLM 配置失败：{e}")
            import traceback
            traceback.print_exc()
            self.runtime_provider = None
            self.llm_client = None
    
    async def _get_previous_chapters(self, novel_id: str, current_chapter: int, count: int = 3) -> List[Dict[str, Any]]:
        """获取前 N 章内容"""
        try:
            from app.novel_db import get_novel_database
            db = get_novel_database()
            
            prev_chapters = []
            start = max(1, current_chapter - count)
            for i in range(start, current_chapter):
                chapter = db.get_chapter(novel_id, i)
                if chapter and chapter.get('content'):
                    prev_chapters.append({
                        'chapter_num': i,
                        'title': chapter.get('title', ''),
                        'content': chapter.get('content', '')
                    })
            
            return prev_chapters
        except Exception as e:
            logger.error(f"获取前章内容失败：{e}")
            return []
    
    async def _refine_outline_smart(self, outline: str, style: str, prev_chapters: List[Dict], 
                                     macro_plot: Optional[Dict], protagonist_halo: Optional[Dict],
                                     novel_id: str, current_chapter: int, style_strength: Optional[str] = None) -> str:
        """智能细化大纲 - 集成记忆系统"""
        from app.services.story_memory import StoryMemory
        
        # 获取记忆上下文
        memory = StoryMemory()
        context = memory.get_story_context(novel_id, current_chapter)
        memory_prompt = memory.format_context_for_prompt(context)

        prev_summary = "\n".join([
            f"- 第{c.get('chapter_num')}章：{_truncate_text(c.get('content', ''), 120)}"
            for c in prev_chapters[-2:]
        ]) if prev_chapters else "无"

        macro_summary = _truncate_text(str(macro_plot or {}), 300)
        halo_summary = _truncate_text(str(protagonist_halo or {}), 200)
        memory_summary = _truncate_text(memory_prompt, 500)

        outline_to_use = (
            f"原始续写要求：{_truncate_text(outline, 600)}\n\n"
            f"最近章节摘要：\n{prev_summary}\n\n"
            f"宏观规划摘要：{macro_summary or '无'}\n"
            f"主角设定摘要：{halo_summary or '无'}\n"
            f"故事记忆参考：{memory_summary or '无'}"
        )

        try:
            return await self._refine_outline(outline_to_use, style, style_strength=style_strength)
        except TypeError as e:
            if 'style_strength' in str(e):
                return await self._refine_outline(outline_to_use, style)
            raise
    
    async def _prepare_characters_smart(self, novel_id: str, outline: str, prev_chapters: List[Dict],
                                          world_map: Optional[Dict], protagonist_halo: Optional[Dict]) -> Dict[str, Any]:
        """智能准备角色 - 集成记忆系统，返回角色笔记与结构化状态包"""
        from app.services.story_memory import StoryMemory
        
        memory = StoryMemory()
        chars = memory.get_characters(novel_id)
        char_notes = "\n".join([f"- {c['character_name']}: {c.get('status', '')} {c.get('personality', '')}" for c in chars]) if chars else ""

        prev_summary = "\n".join([
            f"- 第{c.get('chapter_num')}章：{_truncate_text(c.get('content', ''), 100)}"
            for c in prev_chapters[-2:]
        ]) if prev_chapters else "无"
        world_summary = _truncate_text(str(world_map or {}), 250)
        halo_summary = _truncate_text(str(protagonist_halo or {}), 180)
        character_context = _truncate_text(char_notes, 400)

        compact_outline = (
            f"续写需求：{_truncate_text(outline, 500)}\n\n"
            f"最近章节：\n{prev_summary}\n\n"
            f"世界观摘要：{world_summary or '无'}\n"
            f"主角设定：{halo_summary or '无'}\n"
            f"现有角色档案：\n{character_context or '无'}"
        )

        prepared_notes = await self._prepare_characters(novel_id, compact_outline)
        character_state_packet = {
            'protagonist': {
                'name': protagonist_halo.get('name', '主角') if protagonist_halo else '主角',
                'current_goal': protagonist_halo.get('goal', '') if protagonist_halo else '',
                'current_emotion': '保持连续的情绪推进',
                'new_realization': '',
                'injuries_or_limits': [],
                'resources': [],
                'behavior_constraints': ['不得违背既有人物设定']
            },
            'supporting_characters': [
                {
                    'name': c.get('character_name', ''),
                    'current_goal': '',
                    'current_emotion': c.get('status', ''),
                    'new_realization': '',
                    'injuries_or_limits': [],
                    'resources': [],
                    'behavior_constraints': [],
                    'dialogue_tone': c.get('personality', '')
                }
                for c in chars[:5]
            ],
            'relationship_shifts': [],
            'absent_but_relevant_characters': []
        }

        return {
            'character_notes': prepared_notes,
            'character_state_packet': character_state_packet
        }
    
    async def _write_draft_smart(self, outline: str, character_notes: str, word_count_target: int,
                                   style: str, prev_chapters: List[Dict], macro_plot: Optional[Dict],
                                   world_map: Optional[Dict], protagonist_halo: Optional[Dict],
                                   style_strength: Optional[str] = None) -> str:
        """智能撰写初稿 - 使用分段生成器"""
        from app.services.chapter_generator import ChapterGenerator
        
        generator = ChapterGenerator(self._call_llm)
        return await generator.generate_chapter(
            outline=outline,
            word_count_target=word_count_target,
            prev_chapters=prev_chapters,
            character_notes=character_notes,
            world_map=world_map,
            style=style,
            style_strength=style_strength
        )
    
    async def _consistency_check_smart(self, content: str, novel_id: str, prev_chapters: List[Dict],
                                         world_map: Optional[Dict], protagonist_halo: Optional[Dict],
                                         chapter_num: int, style: str = 'default',
                                         style_strength: Optional[str] = None) -> Dict[str, Any]:
        """智能一致性检查 - 集成质量检查器，返回结构化 ReviewPacket"""
        from app.services.quality_checker import QualityChecker
        from app.services.story_memory import StoryMemory
        
        # 质量检查
        checker = QualityChecker()
        quality = checker.check(content, {
            'target_words': 2500,
            'prev_content': prev_chapters[-1].get('content', '') if prev_chapters else ''
        })
        
        # 保存章节记忆
        memory = StoryMemory()
        memory.save_chapter_memory(novel_id, chapter_num, content)

        style_feedback = evaluate_style_hit(content, style, style_strength)
        
        # 将问题分类为 fatal / important / optional
        raw_issues = quality.get('issues', [])
        fatal_issues = [i for i in raw_issues if any(kw in i for kw in ['重复', '跑偏', 'OOC', '断头', '截断'])]
        important_issues = [i for i in raw_issues if any(kw in i for kw in ['一致性', '风格', '字数', '对话'])]
        optional_issues = [i for i in raw_issues if i not in fatal_issues and i not in important_issues]
        
        # 构建 ReviewPacket
        review_packet = {
            'fatal_issues': fatal_issues,
            'important_issues': important_issues,
            'optional_issues': optional_issues,
            'scores': {
                'continuity': quality.get('total_score', 0),
                'plot_progress': 0,
                'character_consistency': 0,
                'style_match': style_feedback.get('score', 0),
                'ending_strength': 0,
                'naturalness': 0,
            },
            'style_feedback': style_feedback,
            'editor_patch_brief': fatal_issues[:2] + important_issues[:2],
            'pass_to_editor': len(fatal_issues) > 0,
        }
        
        # 兼容旧字段
        return {
            'issues': raw_issues,
            'has_issues': not quality.get('pass', True),
            'quality_score': quality.get('total_score', 0),
            'word_count': quality.get('word_count', 0),
            'style_feedback': style_feedback,
            'review_packet': review_packet,
        }

    def _check_chapter_duplication(self, content: str, prev_chapters: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """检查新章节是否与最近一章过度相似。"""
        if not content or not prev_chapters:
            return None

        latest = prev_chapters[-1] or {}
        previous_content = latest.get('content', '')
        if not previous_content:
            return None

        current_norm = _normalize_similarity_text(content)
        previous_norm = _normalize_similarity_text(previous_content)
        if len(current_norm) < 400 or len(previous_norm) < 400:
            return None

        ratio = SequenceMatcher(None, current_norm, previous_norm).ratio()
        if ratio >= 0.82:
            return {
                'similarity_ratio': round(ratio, 3),
                'previous_chapter_num': latest.get('chapter_num')
            }
        return None
    
    async def _complete_ending(self, content: str, style: str = 'default', style_strength: Optional[str] = None) -> str:
        """对不完整的章节结尾进行补尾。"""
        style_config = apply_style_strength(get_author_style(style), style_strength or 'medium')
        tail_context = content[-200:] if len(content) > 200 else content

        prompt = f"""你是一位专业小说编辑。以下章节结尾明显没有写完，停在半句话上。
请只补写结尾部分（约 200~300 字），让本章完整收束。

【已有内容结尾】
{tail_context}

【补尾要求】
1. 从已有内容的结尾自然衔接，不要重复已有内容
2. 收束本章情节，留下合理悬念
3. 最后一句必须是完整句，不能停在半句话上
4. 保持{style_config.get('name', '当前')}的写作风格
5. 只输出补尾正文，不要任何解释

请直接输出补尾内容："""

        try:
            completion = await self._call_llm(prompt, max_tokens=600)
            if completion and len(completion.strip()) > 50:
                return content + "\n\n" + completion.strip()
        except Exception as e:
            logger.warning(f"结尾补全失败：{e}")

        # fallback: 直接返回原文
        return content

    async def _de_ai_polish(self, content: str, style: str = 'default', style_strength: Optional[str] = None) -> str:
        """去AI化润色：消除AI写作腔调，让语言更自然、更有人味。"""
        style_config = apply_style_strength(get_author_style(style), style_strength or 'medium')

        prompt = f"""你是一位资深文学编辑。以下章节含有一些AI写作的典型痕迹，请在不改变剧情和结构的前提下，消除这些AI腔调。

【待处理内容】
{content[:4000]}

【需要消除的AI痕迹类型】
- "眼中闪过一丝"、"嘴角勾起一抹"等套路化描写
- "深吸一口气"、"心中暗道"等高频动作和内心独白模板
- "一股莫名的"、"不禁...起来"、"不由得"等情绪模板
- "与此同时"、"仿佛整个世界都"等连接和夸张模板
- "命运的齿轮"、"一场风暴正在酝酿"等宏大叙事模板
- "令人...的是"、"值得注意的是"等说明文腔
- 千篇一律的情绪描写和比喻

【处理要求】
1. 保留原有剧情、人物、场景和结构
2. 只修改语言腔调，让表达更自然、更像真人作家
3. 保持{style_config.get('name', '当前')}的写作风格
4. 不要大改，只替换AI腔调为更自然的表达
5. 尽量保持原文字数
6. 直接输出处理后的全文，不要解释

请输出去AI化后的章节正文："""

        try:
            result = await self._call_llm(prompt, max_tokens=min(3000, len(content) + 500))
            if result and len(result.strip()) > len(content) * 0.6:
                return result.strip()
        except Exception as e:
            logger.warning(f"去AI化润色失败：{e}")

        return content

    async def _publishability_polish(self, content: str, hits: List[Dict[str, str]]) -> str:
        excerpts = "\n".join(f"- [{hit.get('category')}] {hit.get('excerpt')}" for hit in hits[:8])
        prompt = f"""你是一位平台投稿审校编辑。以下正文存在若干可修复的高风险表达，请在不改变剧情主干的前提下，将这些表达改写为更适合平台投稿的版本。

【命中风险片段】
{excerpts}

【正文】
{content[:4000]}

【处理要求】
1. 只降低风险表达强度，不改变剧情事实
2. 优先做局部改写，不要整章重写
3. 保留冲突、悬念与人物关系
4. 输出完整修订后的正文，不要解释
"""

        try:
            result = await self._call_llm(prompt, max_tokens=min(3000, len(content) + 400))
            if result and len(result.strip()) >= max(80, len(content.strip()) * 0.5):
                return result.strip()
        except Exception as e:
            logger.warning(f"平台友好改写失败：{e}")
        return content

    async def _fanqie_adaptation_polish(self, content: str, diagnostics: Dict[str, Any]) -> str:
        issues = diagnostics.get('issues', []) if diagnostics else []
        issue_lines = "\n".join(f"- {item.get('type')}: {item.get('message')}" for item in issues[:8])
        prompt = f"""你是一位番茄小说编辑。以下章节目前番茄感不足，请在不改变剧情事实的前提下做局部强化，让它更接近番茄可发稿感。

【问题】
{issue_lines}

【正文】
{content[:4000]}

【处理要求】
1. 开头更快进事
2. 中段减少解释停顿，增加推进密度
3. 至少保留一个明确冲突/转折
4. 章末增强追读钩子
5. 不整章重写，只做必要强化
6. 直接输出修订后的完整正文
"""

        try:
            result = await self._call_llm(prompt, max_tokens=min(3200, len(content) + 500))
            if result and len(result.strip()) >= max(100, len(content.strip()) * 0.5):
                return result.strip()
        except Exception as e:
            logger.warning(f"番茄适配润色失败：{e}")
        return content

    async def _qimao_adaptation_polish(self, content: str, diagnostics: Dict[str, Any]) -> str:
        issues = diagnostics.get('issues', []) if diagnostics else []
        issue_lines = "\n".join(f"- {item.get('type')}: {item.get('message')}" for item in issues[:8])
        prompt = f"""你是一位七猫小说编辑。以下章节目前七猫感不足，请在不改变剧情事实的前提下做局部强化，让它更接近七猫可发稿感。

【问题】
{issue_lines}

【正文】
{content[:4000]}

【处理要求】
1. 加强情绪推进的顺滑度
2. 增加场景与感官细节，但不要堆砌辞藻
3. 增强人物互动的层次与潜台词
4. 章末保留柔性拉力，不要改成番茄式硬钩子
5. 不整章重写，只做必要强化
6. 直接输出修订后的完整正文
"""

        try:
            result = await self._call_llm(prompt, max_tokens=min(3200, len(content) + 500))
            if result and len(result.strip()) >= max(100, len(content.strip()) * 0.5):
                return result.strip()
        except Exception as e:
            logger.warning(f"七猫适配润色失败：{e}")
        return content

    async def _continue_chapter_until_complete(self, content: str, chapter_plan: ChapterPlan, word_count_target: int, style: str = 'default', style_strength: Optional[str] = None) -> str:
        style_config = apply_style_strength(get_author_style(style), style_strength or 'medium')
        must_advance = '\n'.join(f"- {item}" for item in chapter_plan.get('must_advance', [])) or '- 推进本章主事件'
        ending_state = chapter_plan.get('ending_state', {}) or {}
        ending_goal = ending_state.get('plot_state') or chapter_plan.get('chapter_goal') or '完成本章剧情推进'
        prompt = f"""你是一位专业小说写手。以下章节尚未真正写完，请只续写本章剩余部分，不要重写前文。

【已有正文结尾】
{content[-1200:]}

【本章必须推进】
{must_advance}

【本章完成条件】
- 让本章真正完成，而不是停在准备阶段
- 让结尾体现：{ending_goal}
- 保持{style_config.get('name', '当前')}风格
- 只续写剩余需要完成的部分
- 续写约 {max(600, word_count_target // 4)} 字
- 最后一句必须是完整句

请直接续写正文："""
        extra = await self._call_llm(prompt, max_tokens=max(1200, int(word_count_target * 0.8)))
        if extra and len(extra.strip()) > 80:
            return content + "\n\n" + extra.strip()
        return content


    def _summarize_content_for_outline(self, content: str) -> str:
        """Generate a lightweight post-write outline/summary from finished content.
        This is a minimal heuristic: takes up to first few sentences and returns a compact summary.
        """
        if not content:
            return ""
        # Normalize newlines, then split into sentences by Chinese period or common punctuation
        text = content.replace("\n", " ")
        # Simple heuristic: split by Chinese period first, then fallback to English period
        parts = []
        for sep in ["。", ".", "！", "!", "？", "?", ";"]:
            if sep in text:
                parts = [p.strip() for p in text.split(sep) if p.strip()]
                break
        if not parts:
            parts = [text.strip()]
        summary = "。".join(parts[:3]).strip()
        if summary and not summary.endswith("。"):
            summary += "。"
        return summary

    async def execute_chapter_workflow(
        self,
        novel_id: str,
        chapter_num: int,
        outline: str,
        word_count_target: int = 3000,
        style: str = 'default',
        style_strength: Optional[str] = None,
        macro_plot: Optional[Dict] = None,
        world_map: Optional[Dict] = None,
        protagonist_halo: Optional[Dict] = None,
        progress_callback=None,  # 新增：进度回调
        min_style_score: int = 50,
    ) -> Dict[str, Any]:
        """
        执行章节创作工作流 - 智能参考系统
        
        核心机制:
        1. 参考宏观大纲（macro_plot）
        2. 参考世界观地图（world_map）
        3. 参考主角光环设定（protagonist_halo）- 新增！
        4. 参考前 3 章内容（保证连续性）
        5. 6 步 Agent 质量审核
        
        流程:
        1. 剧情架构师 - 细化大纲（参考宏观大纲 + 前 3 章 + 主角光环）
        2. 人物设计师 - 准备角色（参考前 3 章 + 世界观 + 主角光环）
        3. 章节写手 - 撰写初稿（参考前 3 章 + 大纲 + 世界观 + 主角光环）
        4. 对话专家 - 打磨对话
        5. 审核编辑 - 一致性检查（参考前 3 章 + 世界观 + 主角光环）
        6. 主编 - 最终审核
        """
        
        if not self.llm_client:
            logger.error("LLM 未配置！")
            return {
                'status': 'error',
                'message': 'LLM 未配置，请先在配置页面设置 API Key'
            }
        
        workflow_id = f"wf_{novel_id}_{chapter_num}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        logger.info(f"开始执行智能章节工作流：{workflow_id}")
        logger.info(f"    小说 ID: {novel_id}")
        logger.info(f"    章节：第{chapter_num}章")
        logger.info(f"    目标字数：{word_count_target}")
        logger.info(f"    风格：{style}")
        logger.info(f"    大纲：{outline[:100]}...")
        
        def _progress(pct, stage):
            logger.info(f"[进度 {pct}%] {stage}")
            if progress_callback:
                try:
                    progress_callback(pct, stage)
                except:
                    pass
        
        try:
            # 获取前 3 章内容
            logger.info(f"读取前 3 章内容...")
            prev_chapters = await self._get_previous_chapters(novel_id, chapter_num)
            if prev_chapters:
                logger.info(f"    获取到 {len(prev_chapters)} 章前文")
            else:
                logger.info(f"    无前章（这是前几章）")
            
            if not macro_plot:
                logger.info(f"    无宏观大纲")
            if not world_map:
                logger.info(f"    无世界观地图")
            if not protagonist_halo:
                logger.info(f"    无主角光环设定")
            
            # Step 1: 剧情架构师 - 细化大纲
            _progress(5, "Step 1/6: 剧情架构师 - 细化大纲")
            try:
                try:
                    refined_outline = await self._refine_outline_smart(
                        outline, style, prev_chapters, macro_plot, protagonist_halo, novel_id, chapter_num, style_strength=style_strength
                    )
                except TypeError as e:
                    if 'style_strength' in str(e):
                        refined_outline = await self._refine_outline_smart(
                            outline, style, prev_chapters, macro_plot, protagonist_halo, novel_id, chapter_num
                        )
                    else:
                        raise
                logger.info(f"✓ Step 1 完成，细化后大纲长度：{len(refined_outline)}")
            except Exception as e:
                logger.error(f"✗ Step 1 失败：{e}")
                raise
            
            # Step 2: 人物设计师 - 准备角色
            _progress(15, "Step 2/6: 人物设计师 - 准备角色")
            try:
                character_result = await asyncio.wait_for(
                    self._prepare_characters_smart(novel_id, refined_outline, prev_chapters, world_map, protagonist_halo),
                    timeout=300
                )
                if isinstance(character_result, dict):
                    character_notes = character_result.get('character_notes', '')
                    character_state_packet = character_result.get('character_state_packet')
                else:
                    character_notes = character_result
                    character_state_packet = None
                logger.info(f"✓ Step 2 完成，角色笔记长度：{len(character_notes)}")
            except Exception as e:
                logger.warning(f"✗ Step 2 失败，回退使用已有角色设定：{e}")
                base_goal = protagonist_halo.get('goal', '') if protagonist_halo else ''
                base_name = protagonist_halo.get('name', '主角') if protagonist_halo else '主角'
                character_notes = f"- {base_name}: 目标={base_goal}\n- 角色约束：不得违背既有人物设定，延续上一章的情绪与行为逻辑"
                character_state_packet = {
                    'protagonist': {
                        'name': base_name,
                        'current_goal': base_goal,
                        'current_emotion': '延续上一章情绪',
                        'new_realization': '',
                        'injuries_or_limits': [],
                        'resources': [],
                        'behavior_constraints': ['不得违背既有人物设定']
                    },
                    'supporting_characters': [],
                    'relationship_shifts': [],
                    'absent_but_relevant_characters': []
                }
            
            # Step 3: 章节写手 - 撰写初稿（关键步骤）
            _progress(30, "Step 3/6: 章节写手 - 撰写初稿")
            try:
                try:
                    # 构建下一章交接棒（从上一章的 baton 推导当前章的推进约束）
                    current_baton = None
                    if prev_chapters and len(prev_chapters) > 0:
                        prev_baton = None
                        for pc in prev_chapters:
                            if pc.get('next_chapter_baton'):
                                prev_baton = pc['next_chapter_baton']
                        if prev_baton:
                            current_baton = prev_baton
                        else:
                            current_baton = {
                                'must_continue_from': prev_chapters[-1].get('content', '')[-200:] if prev_chapters[-1].get('content') else '',
                                'carry_forward_emotion': '延续上一章结尾的情绪状态',
                                'carry_forward_hooks': [],
                                'forbidden_backtracks': ['禁止回头重写上一章已完成的主事件']
                            }
                    
                    try:
                        draft_content = await self._write_draft_smart(
                            refined_outline, 
                            character_notes, 
                            word_count_target,
                            style,
                            prev_chapters,
                            macro_plot,
                            world_map,
                            protagonist_halo,
                            style_strength=style_strength,
                            next_chapter_baton=current_baton
                        )
                    except TypeError as e:
                        if 'next_chapter_baton' in str(e):
                            draft_content = await self._write_draft_smart(
                                refined_outline,
                                character_notes,
                                word_count_target,
                                style,
                                prev_chapters,
                                macro_plot,
                                world_map,
                                protagonist_halo,
                                style_strength=style_strength
                            )
                        else:
                            raise
                except TypeError as e:
                    if 'style_strength' in str(e):
                        draft_content = await self._write_draft_smart(
                            refined_outline,
                            character_notes,
                            word_count_target,
                            style,
                            prev_chapters,
                            macro_plot,
                            world_map,
                            protagonist_halo,
                        )
                    else:
                        raise
                if not draft_content or len(draft_content) < 500:
                    logger.error(f"Step 3 返回内容过短：{len(draft_content) if draft_content else 0}")
                    logger.error(f"   前 200 字符：{draft_content[:200] if draft_content else 'None'}")
                    raise Exception(f"章节写手失败：内容过短 ({len(draft_content) if draft_content else 0}字)")
                logger.info(f"✓ Step 3 完成，初稿字数：{len(draft_content)}")
            except Exception as e:
                logger.error(f"✗ Step 3 失败：{e}")
                raise Exception(f"Step3_write_draft_failed:{e}")
            
            # Step 4: 对话专家 - 打磨对话
            _progress(60, "Step 4/6: 对话专家 - 打磨对话")
            try:
                dialogue_timeout = float(getattr(self, 'dialogue_polish_timeout', DEFAULT_DIALOGUE_POLISH_TIMEOUT))
                try:
                    polished_content = await asyncio.wait_for(
                        self._polish_dialogue(draft_content, style=style, style_strength=style_strength),
                        timeout=dialogue_timeout,
                    )
                except TypeError as e:
                    if 'style_strength' in str(e):
                        polished_content = await asyncio.wait_for(
                            self._polish_dialogue(draft_content, style=style),
                            timeout=dialogue_timeout,
                        )
                    else:
                        raise
                if not polished_content or len(polished_content) < 500:
                    logger.error(f"Step 4 返回内容过短：{len(polished_content) if polished_content else 0}")
                    raise Exception("对话打磨失败：内容过短")
                logger.info(f"✓ Step 4 完成，润色后字数：{len(polished_content)}")
            except asyncio.TimeoutError:
                logger.warning(f"✗ Step 4 超时，回退使用 Step 3 初稿（timeout={dialogue_timeout}s）")
                polished_content = draft_content
            except Exception as e:
                logger.warning(f"✗ Step 4 失败，回退使用 Step 3 初稿：{e}")
                polished_content = draft_content

            # Step 4.5: 去AI化润色 - 消除AI腔调
            _progress(70, "Step 4.5/7: 去AI化润色 - 消除AI腔调")
            try:
                from app.services.quality_checker import QualityChecker
                checker = QualityChecker()
                ai_patterns = checker._check_ai_patterns(polished_content)
                if _should_trigger_de_ai(ai_patterns, polished_content):
                    logger.info(f"检测到 {len(ai_patterns)} 种AI写作痕迹：{', '.join(ai_patterns[:5])}")
                    de_ai_result = await self._de_ai_polish(polished_content, style=style, style_strength=style_strength)
                    if de_ai_result and len(de_ai_result.strip()) >= max(80, len(polished_content.strip()) * 0.35):
                        polished_content = de_ai_result
                        logger.info(f"✓ 去AI化润色完成，处理后字数：{len(polished_content)}")
                    else:
                        logger.warning("去AI化润色结果过短，保留原稿")
                else:
                    logger.info("✓ 未检测到明显AI写作痕迹，跳过此步")
            except Exception as e:
                logger.warning(f"✗ 去AI化润色失败，保留原稿：{e}")
            
            # Step 5: 一致性检查
            _progress(80, "Step 5/6: 审核编辑 - 一致性检查")
            try:
                check_result = await self._consistency_check_smart(
                    polished_content, novel_id, prev_chapters, world_map, protagonist_halo, chapter_num, style=style, style_strength=style_strength
                )
                logger.info(f"✓ Step 5 完成，质量得分：{check_result.get('quality_score', 0)}")
            except Exception as e:
                logger.error(f"✗ Step 5 失败：{e}")
                raise Exception(f"Step5_consistency_check_failed:{e}")
            
            # Step 6: 最终审核
            _progress(90, "Step 6/7: 主编 - 最终审核")
            try:
                try:
                    final_content = await self._final_review(polished_content, check_result, style=style, style_strength=style_strength)
                except TypeError as e:
                    if 'style' in str(e) or 'style_strength' in str(e):
                        final_content = await self._final_review(polished_content, check_result)
                    else:
                        raise
                if not final_content or len(final_content) < 500:
                    logger.warning(f"✗ Step 6 返回内容过短：{len(final_content) if final_content else 0}，回退使用 Step 5 稿件")
                    final_content = polished_content
                else:
                    logger.info(f"✓ Step 6 完成，最终字数：{len(final_content)}")
            except Exception as e:
                if 'ReadTimeout' in str(e) or 'timeout' in str(e).lower() or '内容过短' in str(e):
                    logger.warning(f"✗ Step 6 失败，回退使用 Step 5 稿件：{e}")
                    final_content = polished_content
                else:
                    logger.error(f"✗ Step 6 失败：{e}")
                    raise Exception(f"Step6_final_review_failed:{e}")

            duplicate_check = self._check_chapter_duplication(final_content, prev_chapters)
            if duplicate_check:
                previous_chapter_num = duplicate_check.get('previous_chapter_num', '?')
                ratio = duplicate_check.get('similarity_ratio', 0)
                raise Exception(
                    f"章节内容与第{previous_chapter_num}章过于相似（相似度 {ratio:.1%}），疑似重复续写"
                )

            style_drift = _check_style_drift(check_result, min_score=min_style_score)
            if style_drift:
                missing = ' / '.join(style_drift.get('missing_features', [])[:3])
                raise Exception(
                    f"章节风格稳定性不足（style score={style_drift.get('score')}），缺少核心风格特征：{missing or style_drift.get('summary', '')}"
                )

            carryover_check = _check_chapter_carryover(final_content, prev_chapters)
            if carryover_check:
                previous_chapter_num = carryover_check.get('previous_chapter_num', '?')
                signals = ' / '.join(carryover_check.get('signals', []))
                if chapter_num == 2:
                    logger.warning(
                        f"⚠️ 第2章连续性信号不足，放宽硬门槛继续生成：第{previous_chapter_num}章 -> 第{chapter_num}章，缺少信号：{signals}"
                    )
                else:
                    raise Exception(
                        f"第{chapter_num}章未有效承接第{previous_chapter_num}章结尾状态，缺少连续续写信号：{signals}"
                    )

            # 结尾完整性检查与自动补全
            ending_check = check_ending_completeness(final_content)
            if not ending_check['is_complete']:
                logger.warning(f"章节结尾不完整：{ending_check['reason']}，尝试自动补全")
                try:
                    final_content = await self._complete_ending(final_content, style=style, style_strength=style_strength)
                    logger.info(f"✓ 结尾补全完成，最终字数：{len(final_content)}")
                except Exception as e:
                    logger.warning(f"结尾补全失败，保留原稿：{e}")

            chapter_plan = build_chapter_plan(chapter_num, outline, prev_chapters, check_result.get('style_feedback'))

            publishability = scan_publishability_risks(final_content)
            if publishability['hits']:
                split_hits = _split_publishability_hits(publishability['hits'])
                if split_hits['repairable']:
                    repaired = await self._publishability_polish(final_content, split_hits['repairable'])
                    if repaired and repaired != final_content:
                        final_content = repaired
                        publishability = scan_publishability_risks(final_content)
                remaining_hits = publishability.get('hits', [])
                if remaining_hits:
                    categories = ' / '.join(sorted({hit.get('category', 'unknown') for hit in remaining_hits}))
                    raise Exception(f"章节存在平台投稿高风险内容，无法自动修复：{categories}")

            if style == 'fanqiao':
                fanqie_diagnostics = evaluate_fanqie_feel(final_content)
                if not fanqie_diagnostics.get('pass', True):
                    adapted = await self._fanqie_adaptation_polish(final_content, fanqie_diagnostics)
                    if adapted and adapted != final_content:
                        final_content = adapted
                        fanqie_diagnostics = evaluate_fanqie_feel(final_content)
                    if not fanqie_diagnostics.get('pass', True):
                        issues = fanqie_diagnostics.get('issues', [])
                        issue_types = ' / '.join(issue.get('type', 'unknown') for issue in issues[:4])
                        raise Exception(f"章节未达到番茄平台可发稿基线：{issue_types}")

            if style == 'qimao':
                qimao_diagnostics = evaluate_qimao_feel(final_content)
                if not qimao_diagnostics.get('pass', True):
                    adapted = await self._qimao_adaptation_polish(final_content, qimao_diagnostics)
                    if adapted and adapted != final_content:
                        final_content = adapted
                        qimao_diagnostics = evaluate_qimao_feel(final_content)
                    if not qimao_diagnostics.get('pass', True):
                        issues = qimao_diagnostics.get('issues', [])
                        issue_types = ' / '.join(issue.get('type', 'unknown') for issue in issues[:4])
                        raise Exception(f"章节未达到七猫平台可发稿基线：{issue_types}")

            # 最终长度门槛：至少达到目标的 60%
            min_length = int(word_count_target * 0.6)
            if len(final_content.strip()) < min_length:
                logger.warning(f"章节最终字数 {len(final_content)} 低于门槛 {min_length}（目标 {word_count_target} 的 60%），尝试补写")
                try:
                    extra = await self._complete_ending(final_content, style=style, style_strength=style_strength)
                    if len(extra.strip()) > len(final_content.strip()):
                        final_content = extra
                        logger.info(f"✓ 补写成功，最终字数：{len(final_content)}")
                    else:
                        logger.warning(f"补写结果未增加字数，保留原稿")
                except Exception as e:
                    logger.warning(f"补写失败，保留原稿：{e}")

            # 语义完章检查：如果本章任务还没完成，执行 continuation pass
            completion_result = evaluate_chapter_completion(final_content, chapter_plan, word_count_target)
            if not completion_result.get('is_complete', True):
                logger.warning(f"章节语义上尚未完成：{'; '.join(completion_result.get('reasons', []))}，尝试 continuation pass")
                try:
                    continued = await self._continue_chapter_until_complete(final_content, chapter_plan, word_count_target, style=style, style_strength=style_strength)
                    if len(continued.strip()) > len(final_content.strip()):
                        final_content = continued
                        logger.info(f"✓ continuation pass 完成，最终字数：{len(final_content)}")
                except Exception as e:
                    logger.warning(f"continuation pass 失败，保留原稿：{e}")
            
            logger.info(f"✅ 智能工作流执行成功：{workflow_id}")
            logger.info(f"   总字数：{len(final_content) if final_content else 0}")
            logger.info(f"   参考前章：{len(prev_chapters)}章")
            outline_summary = self._summarize_content_for_outline(final_content)
            chapter_plan = build_chapter_plan(chapter_num, outline_summary or outline, prev_chapters, check_result.get('style_feedback'))
            next_chapter_baton = build_next_chapter_baton(outline_summary, check_result.get('style_feedback'))
            return {
                'status': 'success',
                'workflow_id': workflow_id,
                'chapter_num': chapter_num,
                'content': final_content,
                'word_count': len(final_content),
                'stages_completed': 7,
                'total_stages': 7,
                'outline_summary': outline_summary,
                'style_feedback': check_result.get('style_feedback'),
                'chapter_plan': chapter_plan,
                'next_chapter_baton': next_chapter_baton,
                'character_state_packet': character_state_packet,
                'review_packet': check_result.get('review_packet'),
                'context_used': {
                    'prev_chapters': len(prev_chapters),
                    'macro_plot': macro_plot is not None,
                    'world_map': world_map is not None,
                    'protagonist_halo': protagonist_halo is not None
                }
            }
            
        except Exception as e:
            error_msg = f"工作流执行失败：{str(e)}"
            logger.error(f"❌ {error_msg}")
            import traceback
            logger.error(traceback.format_exc())
            return {
                'status': 'error',
                'message': error_msg,
                'workflow_id': workflow_id
            }
    
    async def _refine_outline(self, outline: str, style: str, style_strength: Optional[str] = None) -> str:
        """剧情架构师：细化大纲"""
        style_config = apply_style_strength(get_author_style(style), style_strength or 'medium')
        strength = style_config.get('strength', 'medium')
        strength_instr = style_config.get('strength_instruction', '')
        style_rules = "\n".join([f"- {item}" for item in style_config.get('guidelines', [])[:4]])
        style_forbidden = "\n".join([f"- {item}" for item in style_config.get('forbidden', [])[:3]])
        style_example = (style_config.get('tone_examples') or [""])[0]
        prompt = f"""你是一位专业的剧情架构师。请细化以下章节大纲，使其更加具体和可执行：

原始大纲：
{outline}

【作家风格参考】
风格名称：{style_config.get('name', '默认风格')}
风格说明：{style_config.get('description', '')}
风格强度：{strength}
强度说明：{strength_instr}
写作守则：
{style_rules}
避免事项：
{style_forbidden}
语感参考：{style_example}

要求：
1. 明确本章的核心冲突
2. 只列出 3 个关键情节点
3. 用一句话说明情感起伏
4. 仅指出 1 个最重要的伏笔或回收点
5. 整体输出控制在 400 字以内
6. 大纲中的节奏、气质和戏剧张力必须体现上述作家风格

请输出细化后的大纲："""

        return await self._call_llm(prompt, max_tokens=700)
    
    async def _prepare_characters(self, novel_id: str, outline: str) -> str:
        """人物设计师：准备角色"""
        try:
            prompt = f"""你是一位人物设计师。根据以下大纲，分析本章可能出现的人物：

大纲：
{outline}

            请列出：
            1. 本章最重要的 2-4 个出场人物
            2. 每个人物一句目标说明
            3. 一句关系动态说明
            4. 一句性格提醒
            5. 整体输出控制在 300 字以内

            输出角色准备笔记："""
            
            logger.info(f"正在调用 LLM 准备角色...")
            result = await self._call_llm(prompt, max_tokens=800)
            logger.info(f"角色准备完成，返回长度：{len(result) if result else 0}")
            return result
        except Exception as e:
            logger.error(f"准备角色失败：{e}")
            import traceback
            traceback.print_exc()
            raise
    
    async def _write_draft(
        self, 
        outline: str, 
        character_notes: str, 
        word_count_target: int,
        style: str
    ) -> str:
        """章节写手：撰写初稿"""
        prompt = f"""你是一位专业的小说写手。请根据以下材料撰写章节正文：

【本章大纲】
{outline}

【角色准备】
{character_notes}

【要求】
1. 字数目标：约{word_count_target}字
2. 使用第三人称叙述
3. 包含动作、对话、心理描写
4. 保持节奏紧凑
5. 展现人物性格

请开始创作："""
        
        return await self._call_llm(prompt, max_tokens=int(word_count_target * 2.2))
    
    async def _polish_dialogue(self, content: str, style: str = 'default', style_strength: Optional[str] = None) -> str:
        """对话专家：打磨对话"""
        content = content or ""
        if len(content) < 500:
            raise ValueError("对话打磨输入内容过短")

        style_config = apply_style_strength(get_author_style(style), style_strength or 'medium')
        style_rules = "\n".join([f"- {item}" for item in style_config.get('guidelines', [])[:4]])
        style_forbidden = "\n".join([f"- {item}" for item in style_config.get('forbidden', [])[:3]])
        style_example = (style_config.get('tone_examples') or [""])[0]

        segments = self._split_dialogue_polish_segments(content)
        polished_segments = []

        for index, segment in enumerate(segments, start=1):
            prompt = f"""你是一位对话专家。请只优化下面这个章节片段中的对话，不要重写整章结构。

【写作风格】
风格名称：{style_config.get('name')}
风格说明：{style_config.get('description')}
风格强度：{style_config.get('strength')}
强度说明：{style_config.get('strength_instruction', '')}
写作守则：
{style_rules}
避免事项：
{style_forbidden}
语感参考：{style_example}

【片段编号】
第 {index}/{len(segments)} 段

【任务要求】
1. 仅微调已有对话与对白附近叙述，保持情节顺序不变
2. 让对话更自然流畅、符合人物性格
3. 增加潜台词，但不要凭空添加重大新情节
4. 尽量保持字数接近原文，允许在 ±15% 浮动
5. 直接输出优化后的片段正文，不要附加说明

【原始片段】
{segment}
"""

            polished_segment = await self._call_llm(prompt, max_tokens=min(4000, max(1800, int(len(segment) * 1.5))))
            if not polished_segment or len(polished_segment) < max(200, len(segment) // 3):
                raise ValueError(f"对话打磨第 {index} 段返回内容过短")
            polished_segments.append(polished_segment.strip())

        merged = "\n\n".join(polished_segments).strip()
        if len(merged) < max(500, len(content) // 2):
            raise ValueError("对话打磨合并结果异常过短")
        return merged

    def _split_dialogue_polish_segments(self, content: str, max_chars: int = 2200) -> List[str]:
        """将长章节按自然段切分，避免单次对话打磨输入过大。"""
        paragraphs = [p for p in content.split("\n\n") if p.strip()]
        if not paragraphs:
            return [content]

        segments: List[str] = []
        current: List[str] = []
        current_len = 0

        for paragraph in paragraphs:
            part_len = len(paragraph) + 2
            if current and current_len + part_len > max_chars:
                segments.append("\n\n".join(current))
                current = [paragraph]
                current_len = part_len
            else:
                current.append(paragraph)
                current_len += part_len

        if current:
            segments.append("\n\n".join(current))

        return segments
    
    async def _consistency_check(self, content: str, novel_id: str) -> Dict[str, Any]:
        """审核编辑：一致性检查"""
        prompt = f"""你是一位审核编辑。请检查以下章节的一致性问题：

【章节内容】
{content}

检查项：
1. 人物性格是否一致
2. 时间线是否合理
3. 地点转换是否流畅
4. 情节逻辑是否通顺
5. 是否有前后矛盾
6. 如果问题很少，请直接回复“无问题”
7. 如果有问题，只列最多 3 条，每条不超过 30 字

请列出发现的问题（如无问题则回复"无问题"）："""

        issues = await self._call_llm(prompt, max_tokens=400)
        
        return {
            'issues': issues,
            'has_issues': '无问题' not in issues
        }
    
    async def _final_review(self, content: str, check_result: Dict, style: str = 'default', style_strength: Optional[str] = None) -> str:
        """主编：最终审核"""
        if not check_result['has_issues']:
            return content

        raw_issues = check_result.get('issues')
        if isinstance(raw_issues, list):
            issue_lines = [str(item).strip() for item in raw_issues if str(item).strip()][:3]
            issues_text = "\n".join(issue_lines)
        else:
            issues_text = str(raw_issues or '').strip()
            issue_lines = [line.strip() for line in issues_text.splitlines() if line.strip()][:3]

        compact_issues = "\n".join(issue_lines) if issue_lines else issues_text[:200]

        if not compact_issues:
            return content

        # 如果审核问题很轻微，直接保留当前稿件，避免整章再次重写导致超时。
        low_risk_markers = ["无问题", "轻微", "少量", "措辞", "个别"]
        if len(compact_issues) < 80 or any(marker in compact_issues for marker in low_risk_markers):
            logger.info("主编审核判定为轻量问题，保留当前稿件不做整章重写")
            return content

        style_config = apply_style_strength(get_author_style(style), style_strength or 'medium')
        style_rules = "\n".join([f"- {item}" for item in style_config.get('guidelines', [])[:4]])
        style_forbidden = "\n".join([f"- {item}" for item in style_config.get('forbidden', [])[:3]])
        style_example = (style_config.get('tone_examples') or [""])[0]
        
        prompt = f"""你是一位主编。请根据审核意见对章节做小范围修订：

【章节内容】
{_truncate_text(content, 3500)}

【审核意见】
{compact_issues}

【作家风格参考】
风格名称：{style_config.get('name')}
风格说明：{style_config.get('description')}
风格强度：{style_config.get('strength')}
强度说明：{style_config.get('strength_instruction', '')}
写作守则：
{style_rules}
避免事项：
{style_forbidden}
语感参考：{style_example}

【修订要求】
1. 只修正审核意见涉及的问题，不要大改剧情
2. 尽量保持原文字数和结构
3. 如果原文基本可用，只做必要微调
4. 直接输出修订后的完整章节，不要解释
5. 最多改动原文的 10%
6. 修订后必须保持上述作家风格，避免回退成通用网文腔

请输出最终版本："""
        
        reviewed = await self._call_llm(prompt, max_tokens=1400)
        if not reviewed or len(reviewed.strip()) < max(500, len(content) // 3):
            raise ValueError("最终审核返回内容过短")
        return reviewed
    
    async def generate_novel_outline(self, title: str, genre: str, description: str, template_id: str = 'qichengzhuanhe') -> Dict[str, Any]:
        """AI 生成小说整体大纲 - 使用专业模板"""
        from app.templates import get_template
        
        # 获取专业模板
        template = get_template('outline', template_id)
        if not template:
            template = get_template('outline', 'qichengzhuanhe')  # 默认使用起承转合
        
        # 填充模板
        prompt = template['template'].format(
            title=title,
            genre=genre,
            description=description
        )
        
        outline = await self._call_llm(prompt, max_tokens=4000)
        
        return {
            'title': title,
            'genre': genre,
            'template_used': template['name'],
            'outline': outline,
            'generated_at': datetime.now().isoformat()
        }
    
    async def generate_characters(self, title: str, genre: str, outline: str, count: int = 5) -> Dict[str, Any]:
        """AI 生成人物设定"""
        prompt = f"""你是一位专业的人物设计师。请为以下小说设计{count}个主要人物：

【小说标题】{title}
【类型】{genre}
【故事大纲】{outline}

请为每个人物设计以下内容：
1. **姓名** (符合类型风格)
2. **年龄/性别**
3. **外貌特征** (3-5 个关键特点)
4. **性格特点** (3-5 个关键词 + 详细说明)
5. **背景故事** (200 字左右)
6. **核心目标** (人物在故事中的追求)
7. **人物关系** (与其他人物的关系)
8. **经典台词** (1-2 句代表性话语)

请按以下 JSON 格式输出（只需要 JSON，不要其他说明）：
{{
  "characters": [
    {{
      "name": "姓名",
      "age": 年龄，
      "gender": "性别",
      "appearance": "外貌描述",
      "personality": ["性格 1", "性格 2"],
      "background": "背景故事",
      "goal": "核心目标",
      "relations": {{"人物名": "关系描述"}},
      "quote": "经典台词",
      "role": "主角/配角/反派"
    }}
  ]
}}"""
        
        response = await self._call_llm(prompt, max_tokens=4000)
        
        # 尝试解析 JSON
        try:
            import json
            # 提取 JSON 部分
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                data = json.loads(json_str)
                return {
                    'characters': data.get('characters', []),
                    'generated_at': datetime.now().isoformat()
                }
        except:
            pass
        
        # 解析失败时返回原始内容
        return {
            'characters': [{'description': response}],
            'generated_at': datetime.now().isoformat()
        }
    
    async def generate_chapter_outline(self, novel_title: str, chapter_num: int, overall_outline: str, context: Optional[Dict[str, Any]] = None, next_chapter_baton: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """AI 生成章节大纲"""
        context = context or {}
        novel_description = context.get('novel_description', '')
        recent_chapters = context.get('recent_chapters', [])
        active_style = context.get('active_style', {})
        known_characters = context.get('known_characters', [])
        unresolved_hooks = context.get('unresolved_hooks', [])
        prev_chapter_plan = context.get('prev_chapter_plan')
        prev_character_state = context.get('prev_character_state')
        prev_review_packet = context.get('prev_review_packet')

        recent_chapter_text = "\n".join([
            f"- 第{chapter.get('chapter_num')}章《{chapter.get('title') or '无题'}》："
            f"大纲={chapter.get('outline') or '无'}；"
            f"正文摘要={chapter.get('content_summary') or chapter.get('content', '')[:200] or '无'}"
            for chapter in recent_chapters[:5]
        ]) or "无"
        style_text = json.dumps(active_style, ensure_ascii=False) if active_style else "默认风格"
        characters_text = "、".join([c.get('name', '') for c in known_characters[:10] if c.get('name')]) or "无"
        hooks_text = "\n".join([f"- {hook.get('description', '')}" for hook in unresolved_hooks[:8]]) or "无"

        # 下一章交接棒提示
        baton_text = ""
        if next_chapter_baton:
            baton_parts = []
            if next_chapter_baton.get('must_continue_from'):
                baton_parts.append(f"- 必须从以下状态继续：{next_chapter_baton['must_continue_from']}")
            if next_chapter_baton.get('carry_forward_emotion'):
                baton_parts.append(f"- 延续情绪：{next_chapter_baton['carry_forward_emotion']}")
            if next_chapter_baton.get('carry_forward_hooks'):
                baton_parts.append(f"- 继续推进的伏笔：{'、'.join(next_chapter_baton['carry_forward_hooks'])}")
            if next_chapter_baton.get('forbidden_backtracks'):
                baton_parts.append(f"- 禁止回头重写：{'、'.join(next_chapter_baton['forbidden_backtracks'])}")
            baton_text = "\n【上一章交接棒】\n" + "\n".join(baton_parts) + "\n"

        # 上一章剧情计划提示
        plan_text = ""
        if prev_chapter_plan:
            plan_parts = []
            if prev_chapter_plan.get('must_advance'):
                plan_parts.append(f"- 上一章推进了：{'、'.join(prev_chapter_plan['must_advance'])}")
            if prev_chapter_plan.get('ending_state', {}).get('plot_state'):
                plan_parts.append(f"- 上一章结尾状态：{prev_chapter_plan['ending_state']['plot_state']}")
            plan_text = "\n【上一章剧情计划】\n" + "\n".join(plan_parts) + "\n"

        prompt = f"""你是一位专业的剧情架构师。请为以下小说的第{chapter_num}章生成详细大纲：

【小说标题】{novel_title}
【小说简介】{novel_description}
【章节号】第{chapter_num}章
【整体大纲】{overall_outline}
【最近章节】
{recent_chapter_text}
【当前创作风格】{style_text}
【已知主要人物】{characters_text}
【未回收伏笔】
{hooks_text}{baton_text}{plan_text}
请生成以下内容：
1. **本章标题** (简洁有力)
2. **核心事件** (本章发生的主要事件，100 字)
3. **情节发展** (开始→发展→高潮→结尾，分 4 段说明)
4. **出场人物** (列出本章出现的人物)
5. **场景设定** (时间、地点、氛围)
6. **伏笔埋设** (如果需要，说明埋设什么伏笔)
7. **情感基调** (紧张/温馨/悲伤/欢乐等)

额外要求：
- ⚠️ 必须与最近章节有明确的情节推进，不能重复已发生的事件
- ⚠️ 仔细阅读【最近章节】中的内容摘要，确保本章大纲与之不同且有承接关系
- ⚠️ 如果最近章节发生了某件事，本章应该展示这件事的后果或新发展
- 必须承接最近章节的因果与情绪，不要重复已发生内容
- 如果存在未回收伏笔，优先选择一个进行推进或加压
- 风格要求要体现在节奏、对白、叙述口吻里
- 输出应便于直接作为写作输入，避免空泛套话
- 如果有【上一章交接棒】，必须严格遵守其中的承接要求和禁止事项

请用清晰的格式输出。"""
        
        outline = await self._call_llm(prompt, max_tokens=2000)
        
        return {
            'chapter_num': chapter_num,
            'outline': outline,
            'outline_summary': _extract_outline_summary(outline),
            'context_used': {
                'recent_chapters': len(recent_chapters),
                'characters': len(known_characters),
                'hooks': len(unresolved_hooks),
                'has_style': bool(active_style),
            },
            'generated_at': datetime.now().isoformat()
        }
    
    async def generate_plot_design(self, chapter_outline: str, characters: List[Dict]) -> Dict[str, Any]:
        """AI 生成情节设计"""
        characters_info = "\n".join([f"- {c.get('name', '人物')}: {c.get('personality', [''])[0] if c.get('personality') else ''}" for c in characters])
        
        prompt = f"""你是一位专业的情节设计师。请根据以下材料设计详细的情节：

【章节大纲】{chapter_outline}
【出场人物】
{characters_info}

请设计：
1. **开场场景** (如何引入本章，200 字)
2. **关键冲突** (人物之间的矛盾或挑战)
3. **转折点** (情节的意外变化)
4. **高潮场景** (本章最精彩的部分，300 字详细描写)
5. **结尾处理** (如何收尾，为下章做铺垫)
6. **对话要点** (关键对话的内容和目的)

请输出详细的情节设计。"""
        
        plot_design = await self._call_llm(prompt, max_tokens=3000)
        
        return {
            'plot_design': plot_design,
            'generated_at': datetime.now().isoformat()
        }
    
    async def _learning_analyst_review(
        self,
        content: str,
        chapter_num: int,
        prev_chapters: List[Dict],
        world_map: Optional[Dict],
        protagonist_halo: Optional[Dict]
    ) -> Dict[str, Any]:
        """学习分析师：质量分析与改进建议"""
        try:
            from app.agents.learning_agent import get_learning_agent
            
            agent = get_learning_agent()
            
            # 分析章节质量
            quality_result = await agent.analyze_chapter_quality(
                content, chapter_num, prev_chapters, world_map, protagonist_halo
            )
            
            # 提取 JSON 结果
            quality_data = self._extract_json(quality_result)
            
            return {
                'quality_score': quality_data.get('scores', {}).get('overall', 0),
                'highlights': quality_data.get('highlights', []),
                'weaknesses': quality_data.get('weaknesses', []),
                'suggestions': quality_data.get('suggestions', []),
                'cool_point_analysis': quality_data.get('cool_point_analysis', {}),
                'writing_style': quality_data.get('writing_style', {})
            }
        except Exception as e:
            logger.error(f"学习分析师失败：{e}")
            return {
                'quality_score': 0,
                'highlights': [],
                'weaknesses': [],
                'suggestions': [],
                'error': str(e)
            }
    
    async def _final_review_with_learning(
        self,
        content: str,
        check_result: Dict[str, Any],
        learning_result: Dict[str, Any]
    ) -> str:
        """主编：最终审核（考虑学习分析师的建议）"""
        # 如果有学习分析建议，进行最终优化
        if learning_result.get('suggestions'):
            suggestions_str = "\n".join(f"- {s}" for s in learning_result['suggestions'][:3])
            
            prompt = f"""你是一位主编。请根据审核意见和学习分析师的建议优化章节。

【章节内容】
{content[:3000]}...

【审核编辑意见】
{check_result.get('issues', '无问题')}

【学习分析师建议】（重点考虑！）
{suggestions_str}

【要求】
1. 采纳学习分析师的合理建议
2. 保持章节整体风格
3. 优化不超过 20% 的内容
4. 确保改进明显但不突兀

请输出优化后的章节（如果无需优化则回复"无需优化"）："""
            
            try:
                optimized = await self._call_llm(prompt, max_tokens=3500)
                if optimized and "无需优化" not in optimized:
                    logger.info(f"主编优化：采纳了学习分析师的建议")
                    return optimized
            except Exception as e:
                logger.error(f"主编优化失败：{e}")
        
        # 无需优化或优化失败，返回原内容
        return content
    
    def _resolve_llm_timeout(self, max_tokens: int) -> httpx.Timeout:
        """为不同重量的写作步骤提供足够长但有限的超时。"""
        base_timeout = int(self.llm_client.get('timeout', 60) or 60) if self.llm_client else 60
        if max_tokens <= 1000:
            read_timeout = max(base_timeout, 180)
        elif max_tokens <= 2500:
            read_timeout = max(base_timeout, 300)
        elif max_tokens <= 4000:
            read_timeout = max(base_timeout, 480)
        else:
            read_timeout = max(base_timeout, 600)
        return httpx.Timeout(connect=30.0, read=float(read_timeout), write=30.0, pool=30.0)

    async def _call_llm(self, prompt: str, max_tokens: int = 2000) -> str:
        """调用 LLM API"""
        if not self.llm_client:
            raise Exception("LLM 未配置")
        
        api_key = self.llm_client['api_key']
        base_url = self.llm_client['base_url'].rstrip('/')
        model = self.llm_client['model']
        timeout = self.llm_client.get('timeout', 300)
        
        headers = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': model,
            'messages': [
                {'role': 'user', 'content': prompt}
            ],
            'max_tokens': max_tokens,
            'max_completion_tokens': max_tokens,
            'temperature': 0.7
        }
        
        timeout_cfg = self._resolve_llm_timeout(max_tokens)
        logger.info(f"LLM 调用：max_tokens={max_tokens}，read_timeout={timeout_cfg.read}s")
        
        # 重试机制：最多重试 3 次
        for attempt in range(3):
            try:
                logger.info(f"LLM API 调用中... (尝试 {attempt+1}/3)")
                async with httpx.AsyncClient(timeout=timeout_cfg) as client:
                    endpoint = self.llm_client.get("endpoint", "/v1/chat/completions")
                    if not str(endpoint).startswith('/'):
                        endpoint = f'/{endpoint}'
                    response = await client.post(
                        f"{base_url}{endpoint}",
                        headers=headers,
                        json=payload
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        choice = data['choices'][0]
                        content = choice['message']['content']
                        finish_reason = choice.get('finish_reason', 'unknown')
                        usage = data.get('usage', {})
                        prompt_tokens = usage.get('prompt_tokens', 0)
                        completion_tokens = usage.get('completion_tokens', 0)
                        self.last_llm_meta = {
                            'finish_reason': finish_reason,
                            'prompt_tokens': prompt_tokens,
                            'completion_tokens': completion_tokens,
                            'requested_max_tokens': max_tokens,
                        }
                        logger.info(f"LLM API 调用成功，返回长度：{len(content)}，finish_reason={finish_reason}，prompt_tokens={prompt_tokens}，completion_tokens={completion_tokens}")
                        if finish_reason == 'length':
                            logger.warning(f"⚠️ 模型输出被 max_tokens 截断！请求 max_tokens={max_tokens}，实际返回 {completion_tokens} tokens。请检查提供商是否有服务端限制。")
                        return content
                    else:
                        error_msg = f"LLM API 调用失败：{response.status_code} - {response.text[:200]}"
                        logger.error(error_msg)
                        if attempt < 2:
                            logger.info(f"等待 5 秒后重试...")
                            import asyncio
                            await asyncio.sleep(5)
                        else:
                            raise Exception(error_msg)
            except httpx.ReadTimeout as e:
                logger.error(f"LLM 读取超时（尝试 {attempt+1}/3）: {e}")
                if attempt < 2:
                    logger.info(f"等待 5 秒后重试...")
                    import asyncio
                    await asyncio.sleep(5)
                else:
                    raise Exception(f"LLM 读取超时，重试 3 次失败：{_stringify_exception(e)}")
            except httpx.ReadError as e:
                logger.error(f"网络读取错误（尝试 {attempt+1}/3）: {e}")
                if attempt < 2:
                    logger.info(f"等待 5 秒后重试...")
                    import asyncio
                    await asyncio.sleep(5)
                else:
                    raise Exception(f"网络读取错误，重试 3 次失败：{_stringify_exception(e)}")
            except httpx.ConnectError as e:
                logger.error(f"网络连接错误（尝试 {attempt+1}/3）: {e}")
                if attempt < 2:
                    logger.info(f"等待 5 秒后重试...")
                    import asyncio
                    await asyncio.sleep(5)
                else:
                    raise Exception(f"LLM 网络连接失败，重试 3 次失败：{_stringify_exception(e)}")
            except Exception as e:
                logger.error(f"LLM 调用异常（尝试 {attempt+1}/3）: {e}")
                if attempt < 2:
                    logger.info(f"等待 5 秒后重试...")
                    import asyncio
                    await asyncio.sleep(5)
                else:
                    raise Exception(f"LLM 调用异常：{_stringify_exception(e)}")
        
        raise Exception("LLM 调用失败，已达最大重试次数")
    
    def _extract_json(self, text: str) -> Dict[str, Any]:
        """从文本中提取 JSON"""
        try:
            # 查找 JSON 起始和结束位置
            json_start = text.find('{')
            json_end = text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = text[json_start:json_end]
                import json
                return json.loads(json_str)
            else:
                raise ValueError("未找到 JSON 内容")
        except Exception as e:
            logger.error(f"提取 JSON 失败：{e}")
            # 返回空字典
            return {}


# 全局单例
_workflow_executor: Optional[WritingWorkflowExecutor] = None


def get_workflow_executor() -> WritingWorkflowExecutor:
    """获取工作流执行器单例"""
    global _workflow_executor
    if not get_all_agents():
        try:
            create_agents({})
        except Exception:
            pass
    if _workflow_executor is None:
        _workflow_executor = WritingWorkflowExecutor()
    else:
        # 配置可能在运行时通过前端更新，返回单例前主动刷新，
        # 避免“测试连接成功但实际创作仍提示未配置/生成 0 字”的陈旧配置问题。
        _workflow_executor._load_llm_config()
    return _workflow_executor
