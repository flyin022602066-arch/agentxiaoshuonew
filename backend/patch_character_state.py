# Patch script to integrate CharacterStatePacket
from pathlib import Path

p = Path(__file__).resolve().parent / "app" / "workflow_executor.py"
text = p.read_text(encoding="utf-8")

# 1. Update function signature and return type
old_func_start = '''    async def _prepare_characters_smart(self, novel_id: str, outline: str, prev_chapters: List[Dict],
                                          world_map: Optional[Dict], protagonist_halo: Optional[Dict]) -> str:
        """智能准备角色 - 集成记忆系统"""'''

new_func_start = '''    async def _prepare_characters_smart(self, novel_id: str, outline: str, prev_chapters: List[Dict],
                                          world_map: Optional[Dict], protagonist_halo: Optional[Dict]) -> Dict[str, Any]:
        """智能准备角色 - 集成记忆系统，返回角色笔记与结构化状态包"""'''

text = text.replace(old_func_start, new_func_start)

# 2. Update return statement
old_return = '''        return await self._prepare_characters(novel_id, compact_outline)
    
    async def _write_draft_smart'''

new_return = '''        prepared_notes = await self._prepare_characters(novel_id, compact_outline)
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
    
    async def _write_draft_smart'''

text = text.replace(old_return, new_return)

# 3. Update Step 2 handling
old_step2 = '''                character_notes = await self._prepare_characters_smart(
                    novel_id, refined_outline, prev_chapters, world_map, protagonist_halo
                )
                logger.info(f"✓ Step 2 完成，角色笔记长度：{len(character_notes)}")'''

new_step2 = '''                character_result = await self._prepare_characters_smart(
                    novel_id, refined_outline, prev_chapters, world_map, protagonist_halo
                )
                if isinstance(character_result, dict):
                    character_notes = character_result.get('character_notes', '')
                    character_state_packet = character_result.get('character_state_packet')
                else:
                    character_notes = character_result
                    character_state_packet = None
                logger.info(f"✓ Step 2 完成，角色笔记长度：{len(character_notes)}")'''

text = text.replace(old_step2, new_step2)

# 4. Add character_state_packet to return dict
old_return_dict = '''                'chapter_plan': chapter_plan,
                'next_chapter_baton': next_chapter_baton,
                'context_used': {'''

new_return_dict = '''                'chapter_plan': chapter_plan,
                'next_chapter_baton': next_chapter_baton,
                'character_state_packet': character_state_packet,
                'context_used': {'''

text = text.replace(old_return_dict, new_return_dict)

p.write_text(text, encoding="utf-8")
print("CharacterStatePacket integration patched successfully")
