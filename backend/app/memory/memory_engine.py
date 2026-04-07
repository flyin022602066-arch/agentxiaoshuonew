# ==========================================
# 多 Agent 协作小说系统 - 记忆引擎
# ==========================================

from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
import logging
import json
import asyncio

logger = logging.getLogger(__name__)


class MemoryEngine:
    """
    记忆引擎 - 三层记忆系统
    
    - 短期记忆：最近章节（内存缓存）
    - 中期记忆：卷摘要（SQLite）
    - 长期记忆：全书设定（向量库 + 图谱）
    """
    
    def __init__(self, project_path: str, config: Dict[str, Any] = None):
        self.project_path = Path(project_path)
        self.config = config or {}
        
        # 三层记忆存储
        self.short_term = ShortTermMemory(window_size=10)
        self.mid_term = MidTermMemory(self.project_path / "memory")
        self.long_term = LongTermMemory(self.project_path / "memory", config)
        
        logger.info(f"记忆引擎初始化：{project_path}")
    
    async def retrieve(self, query: Any, context_type: str = "all") -> Any:
        """检索记忆"""
        if isinstance(query, dict):
            # 结构化查询
            query_type = query.get('type')
            
            if query_type == 'character':
                return await self.long_term.get_character(query.get('character_id'))
            elif query_type == 'learning_data':
                return await self.mid_term.get_learning_data(query.get('project_id'))
            elif query_type == 'style':
                return await self.long_term.get_active_style()
        
        # 语义检索
        return await self.long_term.semantic_search(str(query))
    
    async def store(self, data: Dict[str, Any]):
        """存储记忆"""
        data_type = data.get('type')
        
        if data_type == 'chapter':
            # 章节 → 短期 + 中期
            await self.short_term.add(data)
            await self.mid_term.add_chapter_summary(data)
        
        elif data_type == 'character':
            # 人物 → 长期
            await self.long_term.store_character(data)
        
        elif data_type == 'analyzed_work':
            # 分析作品 → 长期
            await self.long_term.store_analyzed_work(data)
        
        elif data_type == 'technique':
            # 技巧 → 长期
            await self.long_term.store_technique(data)
        
        elif data_type == 'learning_data':
            # 学习数据 → 中期
            await self.mid_term.store_learning_data(data)
        
        logger.debug(f"记忆存储：{data_type}")
    
    async def get_character_state(self, character_name: str) -> Dict[str, Any]:
        """获取人物状态"""
        return await self.long_term.get_character(character_name)
    
    async def get_unresolved_plot_threads(self) -> List[Dict]:
        """获取未回收伏笔"""
        return await self.mid_term.get_unresolved_hooks()
    
    async def check_consistency(self, content: str) -> List[Dict]:
        """检查一致性"""
        return await self.long_term.check_consistency(content)
    
    async def get_active_style(self) -> Dict[str, Any]:
        """获取当前激活的风格"""
        return await self.long_term.get_active_style()

    async def apply_technique(self, technique_id: str, context: Dict[str, Any] | None = None) -> str:
        """应用指定写作技巧，返回提示文本。"""
        return await self.long_term.apply_technique(technique_id, context)
    
    async def close(self):
        """关闭记忆引擎"""
        await self.long_term.close()


class ShortTermMemory:
    """短期记忆 - 内存缓存"""
    
    def __init__(self, window_size: int = 10):
        self.window_size = window_size
        self.chapters: List[Dict] = []
    
    async def add(self, chapter_data: Dict):
        self.chapters.append(chapter_data)
        if len(self.chapters) > self.window_size:
            self.chapters.pop(0)
    
    async def get_recent(self, count: int = 5) -> List[Dict]:
        return self.chapters[-count:]


class MidTermMemory:
    """中期记忆 - SQLite 存储"""
    
    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.db_path = self.storage_path / "mid_term.db"
        # 延迟初始化数据库
        self._db_initialized = False
    
    async def _ensure_db_initialized(self):
        """确保数据库已初始化"""
        if not self._db_initialized:
            await self._init_db()
            self._db_initialized = True
    
    async def _init_db(self):
        """初始化数据库（异步）"""
        import aiosqlite
        
        async with aiosqlite.connect(self.db_path) as db:
            # 章节摘要表
            await db.execute('''
                CREATE TABLE IF NOT EXISTS chapter_summaries (
                    id INTEGER PRIMARY KEY,
                    chapter_num INTEGER,
                    summary TEXT,
                    word_count INTEGER,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 伏笔表
            await db.execute('''
                CREATE TABLE IF NOT EXISTS plot_hooks (
                    id INTEGER PRIMARY KEY,
                    hook_id TEXT UNIQUE,
                    description TEXT,
                    chapter_introduced INTEGER,
                    chapter_resolved INTEGER,
                    status TEXT DEFAULT 'unresolved',
                    importance INTEGER
                )
            ''')
            
            # 学习数据表
            await db.execute('''
                CREATE TABLE IF NOT EXISTS learning_data (
                    id INTEGER PRIMARY KEY,
                    project_id TEXT,
                    data_type TEXT,
                    data_json TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            await db.commit()
    
    async def add_chapter_summary(self, chapter_data: Dict):
        """添加章节摘要（异步）"""
        import aiosqlite
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO chapter_summaries (chapter_num, summary, word_count)
                VALUES (?, ?, ?)
            ''', (
                chapter_data.get('chapter_num'),
                chapter_data.get('summary', '')[:1000],
                chapter_data.get('word_count', 0)
            ))
            await db.commit()
    
    async def get_unresolved_hooks(self) -> List[Dict]:
        """获取未回收伏笔（异步）"""
        import aiosqlite
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute('SELECT * FROM plot_hooks WHERE status = ?', ('unresolved',)) as cursor:
                hooks = []
                async for row in cursor:
                    hooks.append({
                        'hook_id': row['hook_id'],
                        'description': row['description'],
                        'chapter_introduced': row['chapter_introduced'],
                        'importance': row['importance']
                    })
                return hooks
    
    async def store_learning_data(self, data: Dict):
        """存储学习数据（异步）"""
        import aiosqlite
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO learning_data (project_id, data_type, data_json)
                VALUES (?, ?, ?)
            ''', (
                data.get('project_id', 'default'),
                data.get('type', 'general'),
                json.dumps(data, ensure_ascii=False)
            ))
            await db.commit()
    
    async def get_learning_data(self, project_id: str) -> List[Dict]:
        """获取学习数据（异步）"""
        import aiosqlite
        
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute('SELECT data_json FROM learning_data WHERE project_id = ?', (project_id,)) as cursor:
                data = []
                async for row in cursor:
                    try:
                        data.append(json.loads(row['data_json']))
                    except:
                        pass
                return data


class LongTermMemory:
    """长期记忆 - 向量库 + 知识图谱"""

    def __init__(self, storage_path: Path, config: Dict[str, Any] = None):
        self.storage_path = storage_path
        self.config = config or {}
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self.characters_file = self.storage_path / "characters.json"
        self.styles_file = self.storage_path / "styles.json"
        self.analyzed_works_file = self.storage_path / "analyzed_works.json"

        self._vector_db = None
        self._consistency_checker = None
        self._init_files()

    def _init_files(self):
        """初始化文件"""
        default_payloads = {
            self.characters_file: [],
            self.analyzed_works_file: [],
            self.styles_file: {"active_style": {}, "techniques": []},
        }

        for file_path, payload in default_payloads.items():
            if not file_path.exists():
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(payload, f, ensure_ascii=False, indent=2)

    def _get_vector_db(self):
        """获取向量数据库"""
        if self._vector_db is None:
            from app.database.vector_db import get_vector_database
            self._vector_db = get_vector_database()
        return self._vector_db

    def _get_consistency_checker(self):
        """获取一致性检查器"""
        if self._consistency_checker is None:
            from app.database.knowledge_graph import get_consistency_checker
            self._consistency_checker = get_consistency_checker()
        return self._consistency_checker

    async def store_character(self, character_data: Dict):
        """存储人物设定"""
        data = self._load_json(self.characters_file)
        data.append(character_data)
        self._save_json(self.characters_file, data)

        vector_db = self._get_vector_db()
        await vector_db.add_text(
            collection_type="characters",
            text_id=character_data.get('character_id', f"char_{len(data)}"),
            content=json.dumps(character_data, ensure_ascii=False),
            metadata={
                'name': character_data.get('name', ''),
                'type': 'character'
            }
        )

    async def get_character(self, character_id: str) -> Optional[Dict]:
        """获取人物设定"""
        data = self._load_json(self.characters_file)
        for char in data:
            if char.get('character_id') == character_id:
                return char
        return None

    async def get_character_by_name(self, name: str) -> Optional[Dict]:
        """根据名称获取人物"""
        data = self._load_json(self.characters_file)
        for char in data:
            if char.get('name') == name:
                return char
        return None

    async def store_analyzed_work(self, work_data: Dict):
        """存储已分析作品"""
        data = self._load_json(self.analyzed_works_file)
        data.append(work_data)
        self._save_json(self.analyzed_works_file, data)

    async def store_technique(self, technique_data: Dict):
        """存储写作技巧"""
        data = self._load_json(self.styles_file)
        if not isinstance(data, dict):
            data = {"active_style": {}, "techniques": []}
        if 'techniques' not in data:
            data['techniques'] = []
        data['techniques'].append(technique_data)
        self._save_json(self.styles_file, data)

    async def get_active_style(self) -> Dict[str, Any]:
        """获取当前激活的风格"""
        data = self._load_json(self.styles_file)
        if not isinstance(data, dict):
            return {}
        return data.get('active_style', {})

    async def set_active_style(self, style_data: Dict):
        """设置当前激活的风格"""
        data = self._load_json(self.styles_file)
        if not isinstance(data, dict):
            data = {"active_style": {}, "techniques": []}
        data['active_style'] = style_data
        self._save_json(self.styles_file, data)

    async def apply_technique(self, technique_id: str, context: Dict[str, Any] | None = None) -> str:
        """根据技巧 ID 返回适用于当前上下文的提示。"""
        data = self._load_json(self.styles_file)
        if not isinstance(data, dict):
            return ""

        techniques = data.get('techniques', [])
        context = context or {}
        for technique in techniques:
            if technique.get('id') == technique_id or technique.get('name') == technique_id:
                description = technique.get('description', '')
                scene_type = context.get('scene_type', '当前场景')
                return f"请在{scene_type}中应用技巧【{technique.get('name', technique_id)}】：{description}".strip()
        return ""

    async def semantic_search(self, query: str, collection_type: str = "all", top_k: int = 5) -> List[Dict]:
        """语义检索 - 使用向量数据库"""
        try:
            vector_db = self._get_vector_db()
            results = await vector_db.search(
                collection_type=collection_type,
                query=query,
                top_k=top_k
            )
            return results
        except Exception as e:
            logger.error(f"语义搜索失败：{e}")
            return []

    async def check_consistency(self, content: str, chapter_num: int = 0) -> List[Dict]:
        """检查一致性 - 使用知识图谱"""
        try:
            checker = self._get_consistency_checker()
            issues = await checker.check_content(content, chapter_num)
            return issues
        except Exception as e:
            logger.error(f"一致性检查失败：{e}")
            return []

    async def extract_and_store_entities(self, content: str, chapter_num: int):
        """从文本中提取并存储实体"""
        try:
            checker = self._get_consistency_checker()
            entities = await checker.extract_entities_from_text(content, chapter_num)

            for char_name in entities.get('characters', []):
                existing = await self.get_character_by_name(char_name)
                if not existing:
                    await self.store_character({
                        'character_id': f"char_{char_name}_{chapter_num}",
                        'name': char_name,
                        'type': 'character',
                        'first_appearance_chapter': chapter_num
                    })

            return entities
        except Exception as e:
            logger.error(f"提取实体失败：{e}")
            return {'characters': [], 'locations': [], 'items': []}

    async def close(self):
        """关闭"""
        if self._vector_db:
            await self._vector_db.close()
        pass

    def _load_json(self, file_path: Path) -> Any:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _save_json(self, file_path: Path, data: Any):
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


# ========== 全局实例 ==========

_memory_engine: Optional[MemoryEngine] = None


def get_memory_engine(project_path: str = None, config: Dict = None) -> MemoryEngine:
    """获取记忆引擎单例"""
    global _memory_engine
    if _memory_engine is None:
        _memory_engine = MemoryEngine(
            project_path or "./projects/default",
            config
        )
    return _memory_engine
