# ==========================================
# 多 Agent 协作小说系统 - 质量检查器
# 自动检查生成内容的质量问题
# ==========================================

import re
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


class QualityChecker:
    """
    章节质量自动检查器
    
    检查项：
    1. 字数检查
    2. 段落结构
    3. 对话比例
    4. 重复内容
    5. AI写作痕迹
    6. 前后连贯性
    """
    
    def check(self, content: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        检查章节质量
        
        Args:
            content: 章节内容
            context: 上下文信息，包含 target_words, prev_content 等
            
        Returns:
            包含评分、问题列表、是否通过的字典
        """
        issues = []
        scores = {}
        
        # 1. 字数检查
        word_count = len(content)
        target = context.get('target_words', 2000) if context else 2000
        if word_count < target * 0.7:
            issues.append({
                'type': 'word_count',
                'severity': 'high',
                'message': f'字数不足：{word_count}字，目标{target}字'
            })
        elif word_count < target * 0.9:
            issues.append({
                'type': 'word_count',
                'severity': 'low',
                'message': f'字数偏少：{word_count}字，目标{target}字'
            })
        scores['word_count'] = min(100, (word_count / target) * 100)
        
        # 2. 段落结构检查
        paragraphs = [p for p in content.split('\n\n') if p.strip()]
        if len(paragraphs) < 5:
            issues.append({
                'type': 'structure',
                'severity': 'medium',
                'message': f'段落太少：{len(paragraphs)}段，建议至少8段'
            })
        scores['structure'] = min(100, (len(paragraphs) / 10) * 100)
        
        # 3. 对话比例检查
        dialogue_ratio = self._check_dialogue_ratio(content)
        if dialogue_ratio < 0.15:
            issues.append({
                'type': 'dialogue',
                'severity': 'medium',
                'message': f'对话比例过低：{dialogue_ratio:.1%}，建议20-40%'
            })
        elif dialogue_ratio > 0.6:
            issues.append({
                'type': 'dialogue',
                'severity': 'low',
                'message': f'对话比例过高：{dialogue_ratio:.1%}，建议20-40%'
            })
        scores['dialogue'] = min(100, dialogue_ratio * 200)
        
        # 4. 重复内容检查
        repeats = self._check_repetition(content)
        if repeats:
            issues.append({
                'type': 'repetition',
                'severity': 'high',
                'message': f'发现重复内容：{repeats[:50]}...'
            })
        scores['originality'] = max(0, 100 - len(repeats) * 20)
        
        # 5. AI痕迹检查
        ai_patterns = self._check_ai_patterns(content)
        if ai_patterns:
            issues.append({
                'type': 'ai_pattern',
                'severity': 'medium',
                'message': f'发现AI写作痕迹：{", ".join(ai_patterns)}'
            })
        scores['naturalness'] = max(0, 100 - len(ai_patterns) * 15)
        
        # 6. 连贯性检查
        if context and context.get('prev_content'):
            coherence = self._check_coherence(content, context['prev_content'])
            scores['coherence'] = coherence
            if coherence < 50:
                issues.append({
                    'type': 'coherence',
                    'severity': 'high',
                    'message': '与前文衔接不自然'
                })
        
        # 综合评分
        total_score = sum(scores.values()) / len(scores) if scores else 0
        
        return {
            'total_score': round(total_score, 1),
            'scores': scores,
            'issues': issues,
            'word_count': word_count,
            'pass': total_score >= 60 and not any(i['severity'] == 'high' for i in issues)
        }
    
    def _check_dialogue_ratio(self, content: str) -> float:
        """检查对话比例"""
        dialogue_matches = re.findall(r'[""""""].*?[""""""]', content)
        dialogue_len = sum(len(m) for m in dialogue_matches)
        return dialogue_len / len(content) if content else 0
    
    def _check_repetition(self, content: str) -> List[str]:
        """检查重复内容"""
        sentences = re.split(r'[。！？]', content)
        seen = set()
        repeats = []
        for s in sentences:
            s = s.strip()
            if len(s) > 10:
                if s in seen:
                    repeats.append(s)
                seen.add(s)
        return repeats
    
    def _check_ai_patterns(self, content: str) -> List[str]:
        """检查AI写作痕迹"""
        patterns = [
            # 结构类 AI 腔
            (r'首先.*?其次.*?最后', '使用首先其次最后结构'),
            (r'总之|综上所述|总而言之', '使用总结性语句'),
            (r'不仅.*?而且.*?还', '使用递进结构'),
            (r'在这个.*?的时代', '使用模板化开头'),
            (r'仿佛.*?一般', '使用仿佛一般结构'),
            # 情绪描写 AI 腔
            (r'眼中闪过一丝', '眼中闪过一丝（AI套路化情绪描写）'),
            (r'嘴角勾起一抹', '嘴角勾起一抹（AI套路化表情描写）'),
            (r'深吸一口气', '深吸一口气（AI高频动作）'),
            (r'心中暗道', '心中暗道（AI内心独白套路）'),
            (r'一股莫名的', '一股莫名的（AI情绪模板）'),
            (r'不禁.*?起来', '不禁...起来（AI情绪模板）'),
            (r'不由得', '不由得（AI高频词）'),
            (r'心头微微一沉', '心头微微一沉（AI情绪模板）'),
            (r'空气仿佛.*?凝固', '空气仿佛凝固（AI氛围模板）'),
            (r'某种.*?预感.*?涌上心头', '某种预感涌上心头（AI情绪模板）'),
            (r'一种.*?感觉.*?涌上心头', '涌上心头（AI情绪模板）'),
            (r'心中.*?五味杂陈', '五味杂陈（AI高频成语）'),
            # 描写类 AI 腔
            (r'与此同时', '与此同时（AI连接词）'),
            (r'仿佛整个世界都', '仿佛整个世界都（AI夸张模板）'),
            (r'空气中弥漫着.*?气息', '空气中弥漫着...气息（AI环境模板）'),
            (r'时间.*?静止', '时间静止（AI夸张模板）'),
            (r'死一般.*?寂静', '死一般寂静（AI环境模板）'),
            (r'犹如.*?一般', '犹如...一般（AI比喻模板）'),
            (r'宛如.*?一般', '宛如...一般（AI比喻模板）'),
            (r'如同.*?一般', '如同...一般（AI比喻模板）'),
            # 节奏类 AI 腔
            (r'他.*?知道.*?这.*?只.*?开始', '这还只是开始（AI悬念模板）'),
            (r'真正的.*?才.*?到来', '真正的...才到来（AI悬念模板）'),
            (r'一场.*?风暴.*?酝酿', '风暴酝酿（AI悬念模板）'),
            (r'命运的齿轮.*?转动', '命运的齿轮（AI宏大叙事模板）'),
            (r'谁也没有想到', '谁也没有想到（AI转折模板）'),
            (r'然而.*?却不知', '然而却不知（AI转折模板）'),
            # 语言类 AI 腔
            (r'令人.*?的是', '令人...的是（AI连接模板）'),
            (r'值得注意的是', '值得注意的是（AI说明文腔）'),
            (r'可以.*?看出', '可以看出（AI说明文腔）'),
            (r'由此可见', '由此可见（AI说明文腔）'),
            (r'毫无疑问', '毫无疑问（AI填充词）'),
            (r'无疑.*?一个', '无疑是一个（AI填充词）'),
        ]
        found = []
        for pattern, desc in patterns:
            if re.search(pattern, content):
                found.append(desc)
        return found
    
    def _check_coherence(self, current: str, previous: str) -> float:
        """检查与前文连贯性"""
        current_words = set(current[:500].split())
        prev_words = set(previous[-500:].split())
        overlap = len(current_words & prev_words)
        return min(100, (overlap / max(len(prev_words), 1)) * 200)
