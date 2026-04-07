# 小说数据库管理模块
# 使用 SQLite 存储小说、章节、人物、设定等

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)


def get_default_novel_db_path() -> Path:
    """小说业务数据库真源路径。"""
    return Path(__file__).resolve().parents[1] / 'data' / 'novels.db'


class NovelDatabase:
    """
    小说数据库管理类
    使用 SQLite 存储小说项目相关的所有数据
    """
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            # 默认使用 backend/data/novels.db 作为唯一真源
            db_path = get_default_novel_db_path()
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建小说表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS novels (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                genre TEXT,
                description TEXT,
                author TEXT DEFAULT 'AI Author',
                status TEXT DEFAULT 'ongoing',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                settings TEXT DEFAULT '{}',
                total_chapters INTEGER DEFAULT 0,
                total_words INTEGER DEFAULT 0
            )
        ''')
        
        # 创建章节表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chapters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                novel_id TEXT NOT NULL,
                chapter_num INTEGER NOT NULL,
                title TEXT,
                outline TEXT,
                outline_summary TEXT,
                content TEXT,
                word_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'draft',
                style_id TEXT,
                techniques TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (novel_id) REFERENCES novels(id),
                UNIQUE(novel_id, chapter_num)
            )
        ''')

        cursor.execute("PRAGMA table_info(chapters)")
        chapter_columns = {row[1] for row in cursor.fetchall()}
        if 'outline_summary' not in chapter_columns:
            cursor.execute("ALTER TABLE chapters ADD COLUMN outline_summary TEXT")
            logger.info("已为 chapters 表补充 outline_summary 列")
        
        # 创建人物表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS characters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                novel_id TEXT NOT NULL,
                name TEXT NOT NULL,
                role TEXT,
                description TEXT,
                traits TEXT DEFAULT '[]',
                relationships TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (novel_id) REFERENCES novels(id)
            )
        ''')
        
        # 创建伏笔表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS plot_hooks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                novel_id TEXT NOT NULL,
                chapter_introduced INTEGER,
                description TEXT,
                hook_type TEXT,
                status TEXT DEFAULT 'unresolved',
                resolved_chapter INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (novel_id) REFERENCES novels(id)
            )
        ''')
        
        # 创建风格融合表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS style_fusions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                novel_id TEXT NOT NULL,
                fusion_name TEXT,
                source_schools TEXT,
                weights TEXT,
                description TEXT,
                features TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (novel_id) REFERENCES novels(id)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger.info(f"小说数据库初始化完成：{self.db_path}")
    
    def _get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _normalize_novel_row(self, row: sqlite3.Row | None) -> Optional[Dict[str, Any]]:
        if not row:
            return None
        novel = dict(row)
        settings = novel.get('settings')
        if isinstance(settings, str):
            try:
                novel['settings'] = json.loads(settings) if settings else {}
            except json.JSONDecodeError:
                novel['settings'] = {}
        elif settings is None:
            novel['settings'] = {}
        return novel
    
    # ========== 小说管理 ==========
    
    def create_novel(self, title: str, genre: str = 'fantasy', description: str = '', 
                     author: str = 'AI Author', settings: Optional[Dict[str, Any]] = None) -> str:
        """创建新小说"""
        import uuid
        novel_id = f"novel_{uuid.uuid4().hex[:8]}"
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO novels (id, title, genre, description, author, settings)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (novel_id, title, genre, description, author, json.dumps(settings or {}, ensure_ascii=False)))
            
            conn.commit()
            logger.info(f"创建新小说：{novel_id} - {title}")
            return novel_id
        except Exception as e:
            logger.error(f"创建小说失败：{e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def get_novel(self, novel_id: str) -> Optional[Dict[str, Any]]:
        """获取小说详情"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT * FROM novels WHERE id = ?', (novel_id,))
            row = cursor.fetchone()
            return self._normalize_novel_row(row)
        except Exception as e:
            logger.error(f"获取小说失败：{e}")
            return None
        finally:
            conn.close()
    
    def get_all_novels(self) -> List[Dict[str, Any]]:
        """获取所有小说"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT * FROM novels ORDER BY updated_at DESC')
            rows = cursor.fetchall()
            return [self._normalize_novel_row(row) for row in rows]
        except Exception as e:
            logger.error(f"获取所有小说失败：{e}")
            return []
        finally:
            conn.close()
    
    def update_novel(self, novel_id: str, **kwargs) -> bool:
        """更新小说信息"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # 构建更新语句
            set_clauses = []
            values = []
            
            for key, value in kwargs.items():
                if key in ['title', 'genre', 'description', 'author', 'status', 'settings']:
                    if key == 'settings' and isinstance(value, dict):
                        value = json.dumps(value, ensure_ascii=False)
                    set_clauses.append(f"{key} = ?")
                    values.append(value)
            
            if not set_clauses:
                return False
            
            set_clauses.append("updated_at = CURRENT_TIMESTAMP")
            values.append(novel_id)
            
            sql = f"UPDATE novels SET {', '.join(set_clauses)} WHERE id = ?"
            cursor.execute(sql, values)
            
            conn.commit()
            logger.info(f"更新小说：{novel_id}")
            return True
        except Exception as e:
            logger.error(f"更新小说失败：{e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def delete_novel(self, novel_id: str) -> bool:
        """删除小说"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # 先删除相关数据
            cursor.execute('DELETE FROM chapters WHERE novel_id = ?', (novel_id,))
            cursor.execute('DELETE FROM characters WHERE novel_id = ?', (novel_id,))
            cursor.execute('DELETE FROM plot_hooks WHERE novel_id = ?', (novel_id,))
            cursor.execute('DELETE FROM style_fusions WHERE novel_id = ?', (novel_id,))
            cursor.execute('DELETE FROM novels WHERE id = ?', (novel_id,))
            
            conn.commit()
            logger.info(f"删除小说：{novel_id}")
            return True
        except Exception as e:
            logger.error(f"删除小说失败：{e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    # ========== 章节管理 ==========
    
    def create_chapter(self, novel_id: str, chapter_num: int, title: str = '', 
                       outline: str = '', outline_summary: Optional[str] = None) -> int:
        """创建新章节"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO chapters (novel_id, chapter_num, title, outline, outline_summary, status)
                VALUES (?, ?, ?, ?, ?, 'draft')
            ''', (novel_id, chapter_num, title, outline, outline_summary))
            
            conn.commit()
            chapter_id = cursor.lastrowid
            logger.info(f"创建章节：{novel_id} 第{chapter_num}章")
            return chapter_id
        except Exception as e:
            logger.error(f"创建章节失败：{e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def get_chapter(self, novel_id: str, chapter_num: int) -> Optional[Dict[str, Any]]:
        """获取章节内容"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT * FROM chapters 
                WHERE novel_id = ? AND chapter_num = ?
            ''', (novel_id, chapter_num))
            
            row = cursor.fetchone()
            return dict(row) if row else None
        except Exception as e:
            logger.error(f"获取章节失败：{e}")
            return None
        finally:
            conn.close()
    
    def get_all_chapters(self, novel_id: str) -> List[Dict[str, Any]]:
        """获取所有章节"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT * FROM chapters 
                WHERE novel_id = ? 
                ORDER BY chapter_num ASC
            ''', (novel_id,))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"获取所有章节失败：{e}")
            return []
        finally:
            conn.close()
    
    def update_chapter(self, novel_id: str, chapter_num: int, 
                       content: str = None, title: str = None,
                       outline: str = None, outline_summary: str = None, status: str = None) -> bool:
        """更新章节内容"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            updates = []
            values = []
            
            if content is not None:
                updates.append("content = ?")
                values.append(content)
                updates.append("word_count = ?")
                values.append(len(content))
            
            if title is not None:
                updates.append("title = ?")
                values.append(title)
            
            if outline is not None:
                updates.append("outline = ?")
                values.append(outline)
            if outline_summary is not None:
                updates.append("outline_summary = ?")
                values.append(outline_summary)
            
            if status is not None:
                updates.append("status = ?")
                values.append(status)
            
            if not updates:
                return False
            
            updates.append("updated_at = CURRENT_TIMESTAMP")
            values.extend([novel_id, chapter_num])
            
            sql = f"UPDATE chapters SET {', '.join(updates)} WHERE novel_id = ? AND chapter_num = ?"
            cursor.execute(sql, values)
            self._update_novel_stats_with_connection(conn, novel_id)
            
            conn.commit()
            logger.info(f"[OK] 更新章节：{novel_id} 第{chapter_num}章")
            return True
        except Exception as e:
            logger.error(f"[FAIL] 更新章节失败：{e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def _update_novel_stats_with_connection(self, conn, novel_id: str):
        """使用现有连接更新小说统计信息（章节数、总字数）"""
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) as total_chapters, COALESCE(SUM(word_count), 0) as total_words
            FROM chapters WHERE novel_id = ?
        ''', (novel_id,))

        stats = cursor.fetchone()
        total_chapters = stats['total_chapters'] or 0
        total_words = stats['total_words'] or 0

        cursor.execute('''
            UPDATE novels SET
                total_chapters = ?,
                total_words = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (total_chapters, total_words, novel_id))

        logger.info(f"[OK] 更新小说统计：{novel_id} - {total_chapters}章，{total_words}字")

    def _update_novel_stats(self, novel_id: str):
        """更新小说统计信息（章节数、总字数）"""
        conn = self._get_connection()
        try:
            self._update_novel_stats_with_connection(conn, novel_id)
            conn.commit()
        except Exception as e:
            logger.error(f"[FAIL] 更新小说统计失败：{e}")
            conn.rollback()
        finally:
            conn.close()
    
    def delete_chapter(self, novel_id: str, chapter_num: int) -> bool:
        """删除章节"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                DELETE FROM chapters 
                WHERE novel_id = ? AND chapter_num = ?
            ''', (novel_id, chapter_num))

            deleted = cursor.rowcount > 0
            if deleted:
                self._update_novel_stats_with_connection(conn, novel_id)
            
            conn.commit()
            logger.info(f"删除章节：{novel_id} 第{chapter_num}章")
            return deleted
        except Exception as e:
            logger.error(f"删除章节失败：{e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    # ========== 人物管理 ==========
    
    def add_character(self, novel_id: str, name: str, role: str = '', 
                      description: str = '', traits: List[str] = None) -> int:
        """添加人物"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            traits_json = json.dumps(traits or [])
            
            cursor.execute('''
                INSERT INTO characters (novel_id, name, role, description, traits)
                VALUES (?, ?, ?, ?, ?)
            ''', (novel_id, name, role, description, traits_json))
            
            conn.commit()
            character_id = cursor.lastrowid
            logger.info(f"添加人物：{novel_id} - {name}")
            return character_id
        except Exception as e:
            logger.error(f"添加人物失败：{e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def get_characters(self, novel_id: str) -> List[Dict[str, Any]]:
        """获取所有人物"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('SELECT * FROM characters WHERE novel_id = ?', (novel_id,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"获取人物失败：{e}")
            return []
        finally:
            conn.close()
    
    def delete_character(self, character_id: int) -> bool:
        """删除人物"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM characters WHERE id = ?', (character_id,))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"删除人物失败：{e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    # ========== 伏笔管理 ==========
    
    def add_plot_hook(self, novel_id: str, description: str, hook_type: str = '', 
                      chapter_introduced: int = 0) -> int:
        """添加伏笔"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO plot_hooks (novel_id, description, hook_type, chapter_introduced)
                VALUES (?, ?, ?, ?)
            ''', (novel_id, description, hook_type, chapter_introduced))
            
            conn.commit()
            hook_id = cursor.lastrowid
            logger.info(f"添加伏笔：{novel_id}")
            return hook_id
        except Exception as e:
            logger.error(f"添加伏笔失败：{e}")
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def get_unresolved_hooks(self, novel_id: str) -> List[Dict[str, Any]]:
        """获取未解决的伏笔"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                SELECT * FROM plot_hooks 
                WHERE novel_id = ? AND status = 'unresolved'
                ORDER BY chapter_introduced ASC
            ''', (novel_id,))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"获取伏笔失败：{e}")
            return []
        finally:
            conn.close()
    
    def resolve_hook(self, hook_id: int, resolved_chapter: int) -> bool:
        """解决伏笔"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                UPDATE plot_hooks 
                SET status = 'resolved', resolved_chapter = ?
                WHERE id = ?
            ''', (resolved_chapter, hook_id))
            
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"解决伏笔失败：{e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    # ========== 统计信息 ==========
    
    def get_novel_stats(self, novel_id: str) -> Dict[str, Any]:
        """获取小说统计信息"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        try:
            # 章节统计
            cursor.execute('''
                SELECT COUNT(*) as total, SUM(word_count) as total_words
                FROM chapters WHERE novel_id = ?
            ''', (novel_id,))
            chapter_stats = cursor.fetchone()
            
            # 人物统计
            cursor.execute('SELECT COUNT(*) FROM characters WHERE novel_id = ?', (novel_id,))
            character_count = cursor.fetchone()[0]
            
            # 伏笔统计
            cursor.execute('''
                SELECT COUNT(*) FROM plot_hooks 
                WHERE novel_id = ? AND status = 'unresolved'
            ''', (novel_id,))
            unresolved_hooks = cursor.fetchone()[0]
            
            return {
                'total_chapters': chapter_stats['total'] or 0,
                'total_words': chapter_stats['total_words'] or 0,
                'total_characters': character_count,
                'unresolved_hooks': unresolved_hooks
            }
        except Exception as e:
            logger.error(f"获取统计信息失败：{e}")
            return {}
        finally:
            conn.close()


# ========== 全局单例 ==========

_novel_db: Optional[NovelDatabase] = None


def get_novel_database() -> NovelDatabase:
    """获取小说数据库单例"""
    global _novel_db
    if _novel_db is None:
        _novel_db = NovelDatabase()
    return _novel_db


if __name__ == '__main__':
    # 测试
    db = get_novel_database()
    
    # 创建测试小说
    novel_id = db.create_novel('测试小说', 'fantasy', '这是一本测试小说')
    print(f"创建小说：{novel_id}")
    
    # 创建章节
    db.create_chapter(novel_id, 1, '第一章', '第一章大纲')
    db.update_chapter(novel_id, 1, content='这是第一章的内容...', title='开始')
    
    # 获取所有章节
    chapters = db.get_all_chapters(novel_id)
    print(f"章节数：{len(chapters)}")
    
    # 获取统计
    stats = db.get_novel_stats(novel_id)
    print(f"统计：{stats}")
