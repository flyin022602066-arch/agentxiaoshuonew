from typing import TypedDict, List

class HookAction(TypedDict, total=False):
    hook_id: str
    description: str
    action: str
    importance: int

class EndingState(TypedDict, total=False):
    plot_state: str
    emotion_state: str
    relationship_state: str
    hook: str

class ChapterPlan(TypedDict, total=False):
    chapter_num: int
    chapter_goal: str
    must_advance: List[str]
    must_not_repeat: List[str]
    scene_progression: List[str]
    hook_actions: List[HookAction]
    ending_state: EndingState
    chapter_memory_point: str
    style_focus: List[str]

class CharacterSnapshot(TypedDict, total=False):
    name: str
    current_goal: str
    current_emotion: str
    new_realization: str
    injuries_or_limits: List[str]
    resources: List[str]
    behavior_constraints: List[str]
    dialogue_tone: str

class RelationshipShift(TypedDict, total=False):
    source: str
    target: str
    before: str
    after: str
    reason: str

class CharacterStatePacket(TypedDict, total=False):
    protagonist: CharacterSnapshot
    supporting_characters: List[CharacterSnapshot]
    relationship_shifts: List[RelationshipShift]
    absent_but_relevant_characters: List[str]

class DraftSelfCheck(TypedDict, total=False):
    did_advance_must_points: bool
    did_repeat_forbidden_events: bool
    ending_reached_target_state: bool
    estimated_memory_point_present: bool

class DraftPacket(TypedDict, total=False):
    content: str
    actual_word_count: int
    scene_coverage: List[str]
    self_check: DraftSelfCheck

class DialoguePolishedPacket(TypedDict, total=False):
    content: str
    dialogue_adjustments: List[str]
    tone_consistency: str

class ScoreBreakdown(TypedDict, total=False):
    continuity: int
    plot_progress: int
    character_consistency: int
    style_match: int
    ending_strength: int
    naturalness: int

class StyleFeedbackPacket(TypedDict, total=False):
    style_id: str
    style_name: str
    score: int
    matched_features: List[str]
    missing_features: List[str]
    summary: str

class ReviewPacket(TypedDict, total=False):
    fatal_issues: List[str]
    important_issues: List[str]
    optional_issues: List[str]
    scores: ScoreBreakdown
    style_feedback: StyleFeedbackPacket
    pass_to_editor: bool

class NextChapterBaton(TypedDict, total=False):
    must_continue_from: str
    carry_forward_emotion: str
    carry_forward_hooks: List[str]
    carry_forward_relationships: List[str]
    forbidden_backtracks: List[str]

class EndingCheck(TypedDict, total=False):
    is_complete: bool
    has_hook: bool
    ending_type: str

class FinalChapterPacket(TypedDict, total=False):
    content: str
    final_word_count: int
    final_outline_summary: str
    chapter_memory_point: str
    next_chapter_baton: NextChapterBaton
    ending_check: EndingCheck
    style_feedback: StyleFeedbackPacket

class LearningPacket(TypedDict, total=False):
    chapter_strengths: List[str]
    chapter_weaknesses: List[str]
    style_reinforcement: List[str]
    next_chapter_advice: List[str]
    anti_patterns_to_avoid: List[str]
