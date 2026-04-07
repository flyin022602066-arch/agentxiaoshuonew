# 小说系统四大优化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 提升AI写小说质量，使其达到番茄/七猫等平台的过稿水平

**Architecture:** 通过分段生成解决字数问题，通过记忆系统保持连贯性，通过自动审核保证质量，通过风格学习适应平台要求

**Tech Stack:** Python, FastAPI, SQLite, httpx, Vue 3

---

### Task 1: 字数控制 - 分段生成策略

**Files:**
- Create: `backend/app/services/chapter_generator.py`
- Modify: `backend/app/workflow_executor.py`

**Goal:** 让系统能稳定生成2000-3000字的章节

**Approach:** 将长章节拆分成3-4个段落分别生成，然后智能合并

- [ ] **Step 1: 创建分段生成器**

```python
# backend/app/services/chapter_generator.py
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class ChapterGenerator:
    """分段章节生成器"""
    
    def __init__(self, llm_client_func):
        self.llm_client_func = llm_client_func
    
    async def generate_chapter(
        self,
        outline: str,
        word_count_target: int = 2500,
        prev_chapters: List[Dict] = None,
        character_notes: str = "",
        world_map: Dict = None,
        style: str = "default"
    ) -> str:
        """生成分段章节"""
        # 计算需要几段
        segment_count = max(3, word_count_target // 800)
        segment_target = word_count_target // segment_count
        
        # 生成段落大纲
        segments = await self._generate_segment_outlines(
            outline, segment_count, prev_chapters, character_notes
        )
        
        # 逐段生成
        full_content = ""
        for i, seg_outline in enumerate(segments):
            seg_content = await self._generate_segment(
                seg_outline, 
                segment_target,
                prev_content=full_content,
                character_notes=character_notes,
                world_map=world_map,
                style=style
            )
            full_content += seg_content
        
        return full_content
    
    async def _generate_segment_outlines(
        self, 
        outline: str, 
        count: int,
        prev_chapters: List[Dict] = None,
        character_notes: str = ""
    ) -> List[str]:
        """生成段落级大纲"""
        prev_context = ""
        if prev_chapters:
            prev_context = "\n".join([f"第{c['chapter_num']}章摘要：{c.get('content', '')[:200]}" for c in prev_chapters[-2:]])
        
        prompt = f"""作为专业小说编辑，请将以下章节大纲拆分成{count}个段落大纲：

【章节大纲】
{outline}

【前文摘要】
{prev_context}

【角色备注】
{character_notes}

要求：
1. 每段约{800}字
2. 段落间有自然过渡
3. 保持情节连贯
4. 每段有明确的小目标

输出格式（每段一行，用---分隔）：
段落1大纲
---
段落2大纲
---
段落3大纲"""
        
        result = await self.llm_client_func(prompt, max_tokens=1000)
        segments = [s.strip() for s in result.split('---') if s.strip()]
        return segments[:count]
    
    async def _generate_segment(
        self,
        segment_outline: str,
        target_words: int,
        prev_content: str = "",
        character_notes: str = "",
        world_map: Dict = None,
        style: str = "default"
    ) -> str:
        """生成单个段落"""
        prev_snippet = ""
        if prev_content:
            prev_snippet = prev_content[-300:]  # 取前文最后300字作为衔接
        
        world_context = ""
        if world_map:
            world_context = f"\n【世界观】{str(world_map)[:500]}"
        
        prompt = f"""你是一位专业的玄幻小说写手。请根据以下要求创作段落正文：

【本段大纲】
{segment_outline}

【前文衔接】（请保持连贯）
{prev_snippet}

【角色备注】
{character_notes}
{world_context}

【要求】
1. 字数：约{target_words}字
2. 第三人称叙述
3. 包含环境描写、心理描写、对话
4. 节奏紧凑，有悬念
5. 符合网文风格
6. 与前文自然衔接
7. 不要重复前文内容

请开始创作正文："""
        
        content = await self.llm_client_func(prompt, max_tokens=target_words + 200)
        return content.strip() + "\n\n"
```

- [ ] **Step 2: 修改workflow_executor使用新分段生成器**

```python
# backend/app/workflow_executor.py 中的 _write_draft_smart 方法改为：
async def _write_draft_smart(self, outline, character_notes, word_count_target, style, prev_chapters, macro_plot, world_map, protagonist_halo):
    from app.services.chapter_generator import ChapterGenerator
    
    generator = ChapterGenerator(self._call_llm)
    return await generator.generate_chapter(
        outline=outline,
        word_count_target=word_count_target,
        prev_chapters=prev_chapters,
        character_notes=character_notes,
        world_map=world_map,
        style=style
    )
```

- [ ] **Step 3: 测试分段生成**

```bash
cd backend
python -c "
import asyncio
from app.workflow_executor import WritingWorkflowExecutor

async def test():
    executor = WritingWorkflowExecutor()
    result = await executor.execute_chapter_workflow(
        novel_id='test',
        chapter_num=1,
        outline='主角觉醒灵根，开始修真之路',
        word_count_target=2500
    )
    print(f'生成字数: {result.get(\"word_count\", 0)}')
    print(f'状态: {result.get(\"status\")}')

asyncio.run(test())
"
```

---

### Task 2: 长期记忆系统

**Files:**
- Create: `backend/app/services/story_memory.py`
- Modify: `backend/app/workflow_executor.py`

**Goal:** 建立故事记忆系统，保持前后连贯

- [ ] **Step 1: 创建记忆系统**

```python
# backend/app/services/story_memory.py
import sqlite3
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class StoryMemory:
    """故事长期记忆系统"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent / 'data' / 'story_memory.db'
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS character_profiles (
                novel_id TEXT,
                character_name TEXT,
                profile TEXT,
                relationships TEXT,
                status TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (novel_id, character_name)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS plot_points (
                novel_id TEXT,
                chapter_num INTEGER,
                event_type TEXT,
                description TEXT,
                importance INTEGER DEFAULT 1,
                resolved INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (novel_id, chapter_num, event_type)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS world_facts (
                novel_id TEXT,
                fact_type TEXT,
                fact_content TEXT,
                PRIMARY KEY (novel_id, fact_type)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chapter_summaries (
                novel_id TEXT,
                chapter_num INTEGER,
                summary TEXT,
                key_events TEXT,
                character_states TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (novel_id, chapter_num)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_chapter_memory(self, novel_id: str, chapter_num: int, content: str):
        """保存章节记忆"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 生成摘要
        summary = content[:500] + "..." if len(content) > 500 else content
        
        cursor.execute('''
            INSERT OR REPLACE INTO chapter_summaries 
            (novel_id, chapter_num, summary, key_events, character_states)
            VALUES (?, ?, ?, ?, ?)
        ''', (novel_id, chapter_num, summary, "", ""))
        
        conn.commit()
        conn.close()
    
    def get_story_context(self, novel_id: str, current_chapter: int) -> Dict[str, Any]:
        """获取当前章节需要的故事上下文"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        context = {
            'characters': [],
            'active_plots': [],
            'world_facts': [],
            'recent_summary': '',
            'unresolved_hooks': []
        }
        
        # 获取角色档案
        cursor.execute('SELECT * FROM character_profiles WHERE novel_id = ?', (novel_id,))
        context['characters'] = [dict(r) for r in cursor.fetchall()]
        
        # 获取未解决伏笔
        cursor.execute('''
            SELECT * FROM plot_points 
            WHERE novel_id = ? AND resolved = 0 
            ORDER BY chapter_num DESC LIMIT 5
        ''', (novel_id,))
        context['unresolved_hooks'] = [dict(r) for r in cursor.fetchall()]
        
        # 获取世界观
        cursor.execute('SELECT * FROM world_facts WHERE novel_id = ?', (novel_id,))
        context['world_facts'] = [dict(r) for r in cursor.fetchall()]
        
        # 获取最近章节摘要
        cursor.execute('''
            SELECT * FROM chapter_summaries 
            WHERE novel_id = ? AND chapter_num < ?
            ORDER BY chapter_num DESC LIMIT 3
        ''', (novel_id, current_chapter))
        summaries = [dict(r) for r in cursor.fetchall()]
        if summaries:
            context['recent_summary'] = "\n".join([s['summary'] for s in reversed(summaries)])
        
        conn.close()
        return context
    
    def update_character_status(self, novel_id: str, character_name: str, status: str):
        """更新角色状态"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO character_profiles 
            (novel_id, character_name, status, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ''', (novel_id, character_name, status))
        conn.commit()
        conn.close()
    
    def add_plot_point(self, novel_id: str, chapter_num: int, event_type: str, description: str, importance: int = 1):
        """添加情节点"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO plot_points 
            (novel_id, chapter_num, event_type, description, importance)
            VALUES (?, ?, ?, ?, ?)
        ''', (novel_id, chapter_num, event_type, description, importance))
        conn.commit()
        conn.close()
    
    def resolve_plot_point(self, novel_id: str, event_type: str):
        """标记情节点已解决"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE plot_points SET resolved = 1 
            WHERE novel_id = ? AND event_type = ?
        ''', (novel_id, event_type))
        conn.commit()
        conn.close()
```

- [ ] **Step 2: 集成到工作流**

在 `execute_chapter_workflow` 中添加记忆调用：

```python
# 在 workflow_executor.py 中
async def execute_chapter_workflow(self, novel_id, chapter_num, outline, ...):
    from app.services.story_memory import StoryMemory
    
    memory = StoryMemory()
    
    # 获取故事上下文
    context = memory.get_story_context(novel_id, chapter_num)
    
    # 使用上下文生成内容
    # ... 现有生成逻辑 ...
    
    # 保存章节记忆
    memory.save_chapter_memory(novel_id, chapter_num, final_content)
```

---

### Task 3: 质量审核系统

**Files:**
- Create: `backend/app/services/quality_checker.py`
- Modify: `backend/app/workflow_executor.py`

**Goal:** 自动检查生成内容的质量问题

- [ ] **Step 1: 创建质量检查器**

```python
# backend/app/services/quality_checker.py
import re
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

class QualityChecker:
    """章节质量自动检查器"""
    
    def check(self, content: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """检查章节质量"""
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
        scores['word_count'] = min(100, (word_count / target) * 100)
        
        # 2. 段落结构检查
        paragraphs = content.split('\n\n')
        if len(paragraphs) < 5:
            issues.append({
                'type': 'structure',
                'severity': 'medium',
                'message': f'段落太少：{len(paragraphs)}段，建议至少8段'
            })
        scores['structure'] = min(100, (len(paragraphs) / 10) * 100)
        
        # 3. 对话比例检查
        dialogue_ratio = self._check_dialogue_ratio(content)
        if dialogue_ratio < 0.2:
            issues.append({
                'type': 'dialogue',
                'severity': 'medium',
                'message': f'对话比例过低：{dialogue_ratio:.1%}，建议20-40%'
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
            if coherence < 60:
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
            'pass': total_score >= 70 and not any(i['severity'] == 'high' for i in issues)
        }
    
    def _check_dialogue_ratio(self, content: str) -> float:
        """检查对话比例"""
        dialogue_matches = re.findall(r'["""].*?["""]', content)
        dialogue_len = sum(len(m) for m in dialogue_matches)
        return dialogue_len / len(content) if content else 0
    
    def _check_repetition(self, content: str) -> str:
        """检查重复内容"""
        sentences = re.split(r'[。！？]', content)
        seen = set()
        for s in sentences:
            s = s.strip()
            if len(s) > 10 and s in seen:
                return s
            seen.add(s)
        return ""
    
    def _check_ai_patterns(self, content: str) -> List[str]:
        """检查AI写作痕迹"""
        patterns = [
            (r'首先.*?其次.*?最后', '使用首先其次最后结构'),
            (r'总之.*?综上所述', '使用总结性语句'),
            (r'不仅.*?而且.*?还', '使用递进结构'),
        ]
        found = []
        for pattern, desc in patterns:
            if re.search(pattern, content):
                found.append(desc)
        return found
    
    def _check_coherence(self, current: str, previous: str) -> float:
        """检查与前文连贯性"""
        # 简单实现：检查关键词重叠
        current_words = set(current[:500].split())
        prev_words = set(previous[-500:].split())
        overlap = len(current_words & prev_words)
        return min(100, (overlap / max(len(prev_words), 1)) * 200)
```

- [ ] **Step 2: 集成到工作流**

在 `execute_chapter_workflow` 末尾添加质量检查：

```python
# 质量检查
checker = QualityChecker()
quality = checker.check(final_content, {
    'target_words': word_count_target,
    'prev_content': prev_content
})

if not quality['pass']:
    # 如果质量不达标，尝试优化
    logger.warning(f"质量检查未通过，得分：{quality['total_score']}")
    logger.warning(f"问题：{[i['message'] for i in quality['issues']]}")
```

---

### Task 4: 风格学习系统

**Files:**
- Create: `backend/app/services/style_learner.py`
- Modify: `backend/app/workflow_executor.py`

**Goal:** 学习并模仿目标平台风格

- [ ] **Step 1: 创建风格学习器**

```python
# backend/app/services/style_learner.py
import json
from pathlib import Path
from typing import Dict, Any, List
import logging

logger = logging.getLogger(__name__)

# 平台风格模板
PLATFORM_STYLES = {
    'fanqiao': {
        'name': '番茄小说',
        'description': '快节奏、强冲突、多悬念',
        'prompt_template': '''你是一位番茄小说风格的写手。请创作以下内容：

风格要求：
1. 节奏快：每段都有情节推进，不要大段环境描写
2. 冲突强：每章至少一个冲突或转折
3. 悬念多：章末留悬念，吸引读者继续阅读
4. 对话多：用对话推进情节，减少叙述
5. 爽点密集：主角要有优势，打脸要快
6. 语言直白：不要文绉绉，用网文常用表达

【前文】
{prev_content}

【本章大纲】
{outline}

请开始创作：''',
        'target_words': 2500,
        'dialogue_ratio': 0.35,
        'paragraph_max': 5,
    },
    'qimao': {
        'name': '七猫小说',
        'description': '细腻描写、情感线、伏笔',
        'prompt_template': '''你是一位七猫小说风格的写手。请创作以下内容：

风格要求：
1. 描写细腻：环境、心理、动作描写要细致
2. 情感丰富：人物之间要有情感互动
3. 伏笔深远：埋设伏笔，为后续做铺垫
4. 节奏适中：不要过快，给读者品味空间
5. 人物立体：每个角色都要有鲜明性格
6. 语言优美：适当使用修辞手法

【前文】
{prev_content}

【本章大纲】
{outline}

请开始创作：''',
        'target_words': 2800,
        'dialogue_ratio': 0.30,
        'paragraph_max': 8,
    }
}

class StyleLearner:
    """风格学习与适配系统"""
    
    def __init__(self):
        self.platform_styles = PLATFORM_STYLES
    
    def get_platform_prompt(self, platform: str, outline: str, prev_content: str = "") -> str:
        """获取平台风格的prompt"""
        style = self.platform_styles.get(platform, self.platform_styles['fanqiao'])
        return style['prompt_template'].format(
            prev_content=prev_content[-500:] if prev_content else "无前文",
            outline=outline
        )
    
    def get_style_config(self, platform: str) -> Dict[str, Any]:
        """获取平台风格配置"""
        return self.platform_styles.get(platform, self.platform_styles['fanqiao'])
    
    def analyze_style(self, text: str) -> Dict[str, Any]:
        """分析文本风格特征"""
        features = {
            'word_count': len(text),
            'paragraph_count': len(text.split('\n\n')),
            'avg_paragraph_length': len(text) / max(len(text.split('\n\n')), 1),
            'dialogue_ratio': self._calc_dialogue_ratio(text),
            'sentence_variety': self._calc_sentence_variety(text),
            'description_ratio': self._calc_description_ratio(text),
        }
        return features
    
    def _calc_dialogue_ratio(self, text: str) -> float:
        import re
        matches = re.findall(r'["""].*?["""]', text)
        return sum(len(m) for m in matches) / len(text) if text else 0
    
    def _calc_sentence_variety(self, text: str) -> float:
        import re
        sentences = re.split(r'[。！？]', text)
        lengths = [len(s) for s in sentences if s.strip()]
        if not lengths:
            return 0
        avg = sum(lengths) / len(lengths)
        variance = sum((l - avg) ** 2 for l in lengths) / len(lengths)
        return variance ** 0.5
    
    def _calc_description_ratio(self, text: str) -> float:
        description_keywords = ['只见', '仿佛', '如同', '宛如', '顿时', '忽然', '突然', '只见']
        count = sum(text.count(kw) for kw in description_keywords)
        return count / max(len(text) / 100, 1)
```

- [ ] **Step 2: 集成到工作流**

```python
# 在 workflow_executor.py 中
async def _write_draft_smart(self, outline, character_notes, word_count_target, style, prev_chapters, macro_plot, world_map, protagonist_halo):
    from app.services.style_learner import StyleLearner
    from app.services.chapter_generator import ChapterGenerator
    
    style_learner = StyleLearner()
    generator = ChapterGenerator(self._call_llm)
    
    # 获取风格配置
    style_config = style_learner.get_style_config(style)
    
    # 使用风格化prompt生成
    return await generator.generate_chapter(
        outline=outline,
        word_count_target=style_config['target_words'],
        prev_chapters=prev_chapters,
        character_notes=character_notes,
        world_map=world_map,
        style=style
    )
```

---

## 验证清单

- [ ] 分段生成能稳定产出2000+字章节
- [ ] 记忆系统能保持前后连贯
- [ ] 质量检查能识别问题章节
- [ ] 风格学习能适配不同平台要求
