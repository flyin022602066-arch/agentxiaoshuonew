# ==========================================
# 多 Agent 协作小说系统 - 故事记忆系统
# 保持小说前后连贯性
# ==========================================

import sqlite3
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class StoryMemory:
    """
    故事长期记忆系统
    
    功能：
    1. 角色档案管理
    2. 情节点跟踪
    3. 世界观设定存储
    4. 章节摘要存储
    5. 伏笔管理
    """
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent / 'data' / 'story_memory.db'
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 角色档案表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS character_profiles (
                novel_id TEXT,
                character_name TEXT,
                profile TEXT DEFAULT '',
                relationships TEXT DEFAULT '',
                status TEXT DEFAULT '',
                personality TEXT DEFAULT '',
                goals TEXT DEFAULT '',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (novel_id, character_name)
            )
        ''')
        
        # 情节点表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS plot_points (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                novel_id TEXT,
                chapter_num INTEGER,
                event_type TEXT,
                description TEXT,
                characters_involved TEXT DEFAULT '',
                importance INTEGER DEFAULT 1,
                resolved INTEGER DEFAULT 0,
                resolution_chapter INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 世界观设定表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS world_facts (
                novel_id TEXT,
                fact_type TEXT,
                fact_content TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (novel_id, fact_type)
            )
        ''')
        
        # 章节摘要表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chapter_summaries (
                novel_id TEXT,
                chapter_num INTEGER,
                summary TEXT,
                key_events TEXT DEFAULT '',
                character_states TEXT DEFAULT '',
                new_characters TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (novel_id, chapter_num)
            )
        ''')
        
        # 伏笔表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS foreshadowing (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                novel_id TEXT,
                chapter_planted INTEGER,
                description TEXT,
                importance INTEGER DEFAULT 1,
                resolved INTEGER DEFAULT 0,
                resolution_chapter INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info(f"故事记忆数据库初始化完成：{self.db_path}")
    
    # ========== 章节记忆 ==========
    
    def save_chapter_memory(
        self,
        novel_id: str,
        chapter_num: int,
        content: str,
        key_events: str = "",
        character_states: str = "",
        new_characters: str = ""
    ):
        """保存章节记忆"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        summary = content[:500] + "..." if len(content) > 500 else content
        
        cursor.execute('''
            INSERT OR REPLACE INTO chapter_summaries 
            (novel_id, chapter_num, summary, key_events, character_states, new_characters)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (novel_id, chapter_num, summary, key_events, character_states, new_characters))
        
        conn.commit()
        conn.close()
    
    # ========== 角色管理 ==========
    
    def save_character_profile(
        self,
        novel_id: str,
        character_name: str,
        profile: str = "",
        relationships: str = "",
        status: str = "",
        personality: str = "",
        goals: str = ""
    ):
        """保存角色档案"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO character_profiles 
            (novel_id, character_name, profile, relationships, status, personality, goals)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (novel_id, character_name, profile, relationships, status, personality, goals))
        
        conn.commit()
        conn.close()
    
    def get_characters(self, novel_id: str) -> List[Dict[str, Any]]:
        """获取所有角色档案"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM character_profiles WHERE novel_id = ?', (novel_id,))
        chars = [dict(r) for r in cursor.fetchall()]
        
        conn.close()
        return chars
    
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
    
    # ========== 情节点管理 ==========
    
    def add_plot_point(
        self,
        novel_id: str,
        chapter_num: int,
        event_type: str,
        description: str,
        characters_involved: str = "",
        importance: int = 1
    ):
        """添加情节点"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO plot_points 
            (novel_id, chapter_num, event_type, description, characters_involved, importance)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (novel_id, chapter_num, event_type, description, characters_involved, importance))
        conn.commit()
        conn.close()
    
    def resolve_plot_point(self, novel_id: str, event_type: str, resolution_chapter: int):
        """标记情节点已解决"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE plot_points SET resolved = 1, resolution_chapter = ?
            WHERE novel_id = ? AND event_type = ?
        ''', (resolution_chapter, novel_id, event_type))
        conn.commit()
        conn.close()
    
    def get_unresolved_plots(self, novel_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """获取未解决的情节点"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM plot_points 
            WHERE novel_id = ? AND resolved = 0 
            ORDER BY chapter_num DESC LIMIT ?
        ''', (novel_id, limit))
        
        plots = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return plots
    
    # ========== 世界观管理 ==========
    
    def save_world_fact(self, novel_id: str, fact_type: str, fact_content: str):
        """保存世界观设定"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO world_facts (novel_id, fact_type, fact_content)
            VALUES (?, ?, ?)
        ''', (novel_id, fact_type, fact_content))
        conn.commit()
        conn.close()
    
    def get_world_facts(self, novel_id: str) -> List[Dict[str, Any]]:
        """获取世界观设定"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM world_facts WHERE novel_id = ?', (novel_id,))
        facts = [dict(r) for r in cursor.fetchall()]
        
        conn.close()
        return facts
    
    # ========== 伏笔管理 ==========
    
    def add_foreshadowing(
        self,
        novel_id: str,
        chapter_planted: int,
        description: str,
        importance: int = 1
    ):
        """埋设伏笔"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO foreshadowing 
            (novel_id, chapter_planted, description, importance)
            VALUES (?, ?, ?, ?)
        ''', (novel_id, chapter_planted, description, importance))
        conn.commit()
        conn.close()
    
    def resolve_foreshadowing(self, novel_id: str, resolution_chapter: int):
        """回收伏笔"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE foreshadowing SET resolved = 1, resolution_chapter = ?
            WHERE novel_id = ? AND resolved = 0
        ''', (resolution_chapter, novel_id))
        conn.commit()
        conn.close()
    
    def get_unresolved_foreshadowing(self, novel_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """获取未回收的伏笔"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM foreshadowing 
            WHERE novel_id = ? AND resolved = 0 
            ORDER BY chapter_planted DESC LIMIT ?
        ''', (novel_id, limit))
        
        hooks = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return hooks
    
    # ========== 上下文获取 ==========
    
    def get_story_context(self, novel_id: str, current_chapter: int) -> Dict[str, Any]:
        """
        获取当前章节需要的故事上下文
        
        Returns:
            包含角色、情节、世界观、前文摘要的字典
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        context = {
            'characters': [],
            'active_plots': [],
            'unresolved_foreshadowing': [],
            'world_facts': [],
            'recent_summary': '',
            'recent_chapters': []
        }
        
        # 获取角色档案
        cursor.execute('SELECT * FROM character_profiles WHERE novel_id = ?', (novel_id,))
        context['characters'] = [dict(r) for r in cursor.fetchall()]
        
        # 获取未解决情节点
        cursor.execute('''
            SELECT * FROM plot_points 
            WHERE novel_id = ? AND resolved = 0 
            ORDER BY chapter_num DESC LIMIT 5
        ''', (novel_id,))
        context['active_plots'] = [dict(r) for r in cursor.fetchall()]
        
        # 获取未回收伏笔
        cursor.execute('''
            SELECT * FROM foreshadowing 
            WHERE novel_id = ? AND resolved = 0 
            ORDER BY chapter_planted DESC LIMIT 5
        ''', (novel_id,))
        context['unresolved_foreshadowing'] = [dict(r) for r in cursor.fetchall()]
        
        # 获取世界观
        cursor.execute('SELECT * FROM world_facts WHERE novel_id = ?', (novel_id,))
        context['world_facts'] = [dict(r) for r in cursor.fetchall()]
        
        # 获取最近3章摘要
        cursor.execute('''
            SELECT * FROM chapter_summaries 
            WHERE novel_id = ? AND chapter_num < ?
            ORDER BY chapter_num DESC LIMIT 3
        ''', (novel_id, current_chapter))
        summaries = [dict(r) for r in cursor.fetchall()]
        
        if summaries:
            context['recent_chapters'] = list(reversed(summaries))
            context['recent_summary'] = "\n".join([
                f"第{s['chapter_num']}章：{s['summary']}"
                for s in reversed(summaries)
            ])
        
        conn.close()
        return context
    
    def format_context_for_prompt(self, context: Dict[str, Any]) -> str:
        """将上下文格式化为prompt可用的字符串"""
        parts = []
        
        if context.get('characters'):
            chars_info = "\n".join([
                f"- {c['character_name']}：{c.get('status', '')} {c.get('personality', '')}"
                for c in context['characters']
            ])
            parts.append(f"【角色状态】\n{chars_info}")
        
        if context.get('active_plots'):
            plots_info = "\n".join([
                f"- {p['event_type']}：{p['description']}"
                for p in context['active_plots']
            ])
            parts.append(f"【进行中的情节】\n{plots_info}")
        
        if context.get('unresolved_foreshadowing'):
            hooks_info = "\n".join([
                f"- {h['description']}"
                for h in context['unresolved_foreshadowing']
            ])
            parts.append(f"【待回收的伏笔】\n{hooks_info}")
        
        if context.get('recent_summary'):
            parts.append(f"【前文摘要】\n{context['recent_summary']}")
        
        return "\n\n".join(parts)
