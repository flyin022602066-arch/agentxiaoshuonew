import asyncio
import json
from difflib import SequenceMatcher

from app.novel_db import get_novel_database
from app.services.writing_service import WritingService


def normalize_text(text: str, max_chars: int = 1800) -> str:
    return "".join((text or "").split())[:max_chars]


async def main():
    db = get_novel_database()
    service = WritingService()

    settings = {
        "world_map": {
            "world_name": "九州残陆",
            "era": "灵潮复苏初期",
            "power_system": {"name": "灵纹修行"},
        },
        "macro_plot": {
            "volumes": [
                {
                    "volume_num": 1,
                    "main_goal": "查明黑石来历并摆脱追兵",
                    "conflict": "黑石会引来多方势力争夺，主角必须在逃亡中成长",
                }
            ]
        },
        "character_system": {
            "protagonist": {
                "name": "林川",
                "goal": "弄清黑石秘密并活下去",
                "background": "废城长大的孤儿，擅长在险境中求生",
                "personality": ["冷静", "谨慎", "韧性强"],
            }
        },
        "hook_network": {
            "short_term": [
                {"description": "黑石在危险时会发热并指向未知地点", "reveal_chapter": 3},
                {"description": "医院追兵背后另有势力指使", "reveal_chapter": 4},
            ]
        },
        "active_style": {"style_id": "wuxia_gulong", "strength": "strong"},
        "creative_settings": {"style_id": "wuxia_gulong", "strength": "strong", "techniques": []},
    }

    novel_id = db.create_novel(
        title="五章续写实测",
        genre="玄幻",
        description="少年林川得到神秘黑石后遭到追杀，在逃亡中逐步揭开黑石与古老祭坛的秘密。",
        settings=settings,
    )

    outlines = [
        "第一章：林川在废城边缘得到黑石，并在夜里第一次遭遇神秘追兵，仓促逃离藏身处。",
        "第二章：承接逃亡，林川闯入旧医院躲避追兵，在混乱中发现黑石会短暂预警危险，最终冒险脱身。",
        "第三章：承接第二章结尾，林川带着黑石逃到城外废桥，发现黑石表面浮现古老纹路，并被引向废弃祭坛。",
        "第四章：林川进入祭坛外围，首次确认追兵背后另有势力操控，同时在祭坛机关中获得关于黑石来历的残缺线索。",
        "第五章：林川利用新线索设局反制追兵，逼出幕后势力一名执事现身，并为下一阶段远行埋下动机。",
    ]

    previous_content = ""
    results = []

    for index, outline in enumerate(outlines, start=1):
        print(f"\n{'=' * 80}")
        print(f"开始生成第{index}章")
        print(f"大纲：{outline}")
        result = await service.create_chapter_workflow(
            {
                "novel_id": novel_id,
                "chapter_num": index,
                "outline": outline,
                "word_count_target": 3000,
                "style": "wuxia_gulong",
                "style_context": {"style_id": "wuxia_gulong", "strength": "strong"},
                "creative_settings": {"style_id": "wuxia_gulong", "strength": "strong", "techniques": []},
            }
        )

        chapter = db.get_chapter(novel_id, index)
        content = (chapter or {}).get("content") or result.get("content", "")
        ratio = None
        if previous_content and content:
            ratio = SequenceMatcher(None, normalize_text(previous_content), normalize_text(content)).ratio()

        chapter_report = {
            "chapter_num": index,
            "status": result.get("status"),
            "word_count": result.get("word_count", len(content or "")),
            "saved": bool(chapter and chapter.get("content")),
            "similarity_to_prev": round(ratio, 3) if ratio is not None else None,
            "message": result.get("message"),
            "preview": (content or "")[:180],
        }
        results.append(chapter_report)

        print(json.dumps(chapter_report, ensure_ascii=False, indent=2))

        if result.get("status") != "success":
            print("生成中断，后续章节不再继续。")
            break

        previous_content = content

    print(f"\n{'=' * 80}")
    print("五章测试汇总")
    print(json.dumps({"novel_id": novel_id, "results": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
