# ==========================================
# 多 Agent 协作小说系统 - 风格学习系统
# 学习并适配不同小说平台的写作风格
# ==========================================

from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


# 平台风格模板配置
PLATFORM_STYLES = {
    'fanqiao': {
        'name': '番茄小说',
        'description': '快节奏、强冲突、多悬念、爽文风格',
        'prompt_template': '''你是一位番茄小说风格的写手。请创作以下内容：

风格要求：
1. 节奏快：每段都有情节推进，不要大段环境描写
2. 冲突强：每章至少一个冲突或转折
3. 悬念多：章末留悬念，吸引读者继续阅读
4. 对话多：用对话推进情节，减少叙述
5. 爽点密集：主角要有优势，打脸要快
6. 语言直白：不要文绉绉，用网文常用表达
7. 情绪饱满：让读者有代入感

【前文衔接】
{prev_content}

【本章大纲】
{outline}

【角色状态】
{character_notes}

请开始创作：''',
        'target_words': 2500,
        'dialogue_ratio': 0.35,
        'paragraph_max': 5,
    },
    'qimao': {
        'name': '七猫小说',
        'description': '细腻描写、情感线、伏笔、慢热',
        'prompt_template': '''你是一位七猫小说风格的写手。请创作以下内容：

风格要求：
1. 描写细腻：环境、心理、动作描写要细致
2. 情感丰富：人物之间要有情感互动
3. 伏笔深远：埋设伏笔，为后续做铺垫
4. 节奏适中：不要过快，给读者品味空间
5. 人物立体：每个角色都要有鲜明性格
6. 语言优美：适当使用修辞手法
7. 细节丰富：让场景更加生动

【前文衔接】
{prev_content}

【本章大纲】
{outline}

【角色状态】
{character_notes}

请开始创作：''',
        'target_words': 2800,
        'dialogue_ratio': 0.30,
        'paragraph_max': 8,
    },
    'qidian': {
        'name': '起点中文网',
        'description': '世界观宏大、升级流、热血',
        'prompt_template': '''你是一位起点中文网风格的写手。请创作以下内容：

风格要求：
1. 世界观宏大：展现广阔的世界观设定
2. 升级流：主角要有明确的成长路径
3. 热血激昂：战斗场面要热血
4. 设定严谨：力量体系要自洽
5. 群像描写：配角也要有血有肉
6. 节奏张弛有度：紧张与放松交替

【前文衔接】
{prev_content}

【本章大纲】
{outline}

【角色状态】
{character_notes}

请开始创作：''',
        'target_words': 3000,
        'dialogue_ratio': 0.30,
        'paragraph_max': 6,
    },
    'default': {
        'name': '默认风格',
        'description': '通用网文风格',
        'prompt_template': '''你是一位专业的网络小说写手。请创作以下内容：

【前文衔接】
{prev_content}

【本章大纲】
{outline}

【角色状态】
{character_notes}

要求：
1. 第三人称叙述
2. 包含环境描写、心理描写、对话
3. 节奏紧凑，有悬念
4. 符合网文风格
5. 与前文自然衔接

请开始创作：''',
        'target_words': 2500,
        'dialogue_ratio': 0.30,
        'paragraph_max': 6,
    }
}


class StyleLearner:
    """
    风格学习与适配系统
    
    功能：
    1. 提供不同平台的风格模板
    2. 分析文本风格特征
    3. 适配目标平台要求
    """
    
    def __init__(self):
        self.platform_styles = PLATFORM_STYLES
    
    def get_platform_prompt(
        self,
        platform: str,
        outline: str,
        prev_content: str = "",
        character_notes: str = ""
    ) -> str:
        """获取平台风格的prompt"""
        style = self.platform_styles.get(platform, self.platform_styles['default'])
        return style['prompt_template'].format(
            prev_content=prev_content[-500:] if prev_content else "无前文",
            outline=outline,
            character_notes=character_notes or "无特殊备注"
        )
    
    def get_style_config(self, platform: str) -> Dict[str, Any]:
        """获取平台风格配置"""
        return self.platform_styles.get(platform, self.platform_styles['default'])
    
    def analyze_style(self, text: str) -> Dict[str, Any]:
        """分析文本风格特征"""
        features = {
            'word_count': len(text),
            'paragraph_count': len([p for p in text.split('\n\n') if p.strip()]),
            'avg_paragraph_length': len(text) / max(len([p for p in text.split('\n\n') if p.strip()]), 1),
            'dialogue_ratio': self._calc_dialogue_ratio(text),
            'sentence_variety': self._calc_sentence_variety(text),
            'description_ratio': self._calc_description_ratio(text),
        }
        return features
    
    def match_platform(self, text: str) -> str:
        """分析文本最接近哪个平台风格"""
        features = self.analyze_style(text)
        
        # 简单匹配逻辑
        if features['dialogue_ratio'] > 0.35 and features['avg_paragraph_length'] < 100:
            return 'fanqiao'
        elif features['description_ratio'] > 0.1:
            return 'qimao'
        elif features['word_count'] > 2800:
            return 'qidian'
        else:
            return 'default'
    
    def _calc_dialogue_ratio(self, text: str) -> float:
        """计算对话比例"""
        import re
        matches = re.findall(r'[""""""].*?[""""""]', text)
        return sum(len(m) for m in matches) / len(text) if text else 0
    
    def _calc_sentence_variety(self, text: str) -> float:
        """计算句子变化度"""
        import re
        sentences = re.split(r'[。！？]', text)
        lengths = [len(s) for s in sentences if s.strip()]
        if not lengths:
            return 0
        avg = sum(lengths) / len(lengths)
        variance = sum((l - avg) ** 2 for l in lengths) / len(lengths)
        return variance ** 0.5
    
    def _calc_description_ratio(self, text: str) -> float:
        """计算描写比例"""
        description_keywords = ['只见', '仿佛', '如同', '宛如', '顿时', '忽然', '突然', '只见', '仿佛看到', '宛如']
        count = sum(text.count(kw) for kw in description_keywords)
        return count / max(len(text) / 100, 1)
