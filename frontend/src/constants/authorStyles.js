export const authorStyles = [
  {
    id: 'default',
    category: '通用',
    name: '默认风格',
    description: '通用网络小说写作风格，强调清晰叙事、稳定节奏与可读性。',
    features: ['通用叙事', '节奏稳定', '适配性强'],
    forbidden: ['避免大段空泛抒情', '避免无意义重复描写', '避免角色口吻完全同质化'],
    toneExample: '语言自然流畅，兼顾剧情推进与阅读顺滑感。'
  },
  {
    id: 'wuxia_jinyong',
    category: '传统作家',
    name: '金庸派',
    description: '重人物群像、门派江湖、家国气与正统武侠叙事。',
    features: ['人物立体', '江湖氛围', '叙事稳健', '门派体系'],
    forbidden: ['避免过于现代的网络口头禅', '避免无来由的装酷式短句堆叠', '避免只顾打斗不顾人物缘起'],
    toneExample: '夜色沉沉，长街寂寂，惟有檐角风铃轻响，似也在替旧日恩仇低声叹息。'
  },
  {
    id: 'wuxia_gulong',
    category: '传统作家',
    name: '古龙派',
    description: '强调凝练短句、留白、冷峻气质与戏剧张力。',
    features: ['语言凝练', '气质冷峻', '戏剧感强', '留白锋利'],
    forbidden: ['避免长篇背景讲解', '避免语言过于板正厚重', '避免把人物心理解释得过满'],
    toneExample: '灯很冷。刀也很冷。可他的眼睛，比刀更冷。'
  },
  {
    id: 'romance_qiongyao',
    category: '传统作家',
    name: '琼瑶派',
    description: '强调情感起伏、人物关系纠葛与抒情表达。',
    features: ['情感浓烈', '关系推动', '抒情表达', '冲突外显'],
    forbidden: ['避免冷硬纪实腔', '避免把情绪写得过于克制而失去张力', '避免只谈剧情推进不写关系变化'],
    toneExample: '她望着他，眼里仿佛盛着一整场未曾落尽的雨，哀伤而炽热。'
  },
  {
    id: 'wuxia_liangyusheng',
    category: '传统作家',
    name: '梁羽生派',
    description: '诗意较强，兼重历史感、侠义精神与人物风骨。',
    features: ['诗意笔法', '历史气息', '侠义风骨', '气质清正'],
    forbidden: ['避免语言过于轻佻', '避免只写奇情不写风骨', '避免历史背景完全虚化'],
    toneExample: '长风卷过古道，黄叶满地，行人一骑西来，仿佛也裹着旧时山河的寒意。'
  },
  {
    id: 'wuxia_wenruian',
    category: '传统作家',
    name: '温瑞安派',
    description: '文字灵动跳脱，节奏快，意象强，爆发感足。',
    features: ['文字灵动', '节奏明快', '意象强烈', '爆发感足'],
    forbidden: ['避免平铺直叙到底', '避免动作场面缺少节奏变化', '避免意象疲软无爆发点'],
    toneExample: '剑起时，风像碎了；人未退，心已惊。'
  },
  {
    id: 'literary_zhangailing',
    category: '文学作家',
    name: '张爱玲派',
    description: '擅长细腻世情、人物幽微心理与带冷感的精致观察。',
    features: ['世情观察', '心理细腻', '冷感华美', '细节锋利'],
    forbidden: ['避免热血爽文式直白宣泄', '避免粗线条人物塑造', '避免缺少世情观察的空抒情'],
    toneExample: '她低下头去，像一朵颜色过分浓艳的花，忽然在灯影里暗了一暗。'
  },
  {
    id: 'realism_moyan',
    category: '文学作家',
    name: '莫言派',
    description: '具有强烈生命力与乡土感，现实与荒诞交织，感官描写饱满。',
    features: ['生命力强', '乡土气息', '荒诞现实', '感官饱满'],
    forbidden: ['避免语言过于精致纤弱', '避免人物失去粗粝生命力', '避免场景缺少感官触感'],
    toneExample: '风从土坡上滚下来，带着牲口气、草根气，还有太阳烤裂黄土后的焦苦味。'
  },
  {
    id: 'web_heianhuolong',
    category: '网文作者',
    name: '黑暗火龙派',
    description: '偏升级流与修炼成长线，强调稳步变强、战斗推进、资源争夺和连续爽点回报。',
    features: ['升级流', '修炼推进', '战斗密集', '爽点持续'],
    forbidden: ['避免长时间停留在无推进的日常', '避免修炼体系模糊不清', '避免爽点铺垫过长而迟迟不兑现'],
    toneExample: '真元轰然运转，林辰只觉得体内关窍一寸寸松动，下一瞬，压制许久的壁障终于被一剑劈开。'
  },
  {
    id: 'web_chendong',
    category: '网文作者',
    name: '辰东派',
    description: '擅长宏大世界观、远古秘辛、热血大战与史诗感，常把个人命运放进大时代洪流。',
    features: ['世界宏大', '秘辛感强', '史诗热血', '远古悬念'],
    forbidden: ['避免世界观显得过小', '避免只有个人恩怨没有时代纵深', '避免战斗缺乏恢弘感'],
    toneExample: '苍穹尽头，古老战旗猎猎作响，仿佛一段被尘封万载的血色岁月，正在此刻重新苏醒。'
  },
  {
    id: 'web_tiancantudou',
    category: '网文作者',
    name: '天蚕土豆派',
    description: '强调清晰升级体系、热血逆袭、资源争夺与阶段性高光爆发，阅读节奏顺畅。',
    features: ['体系清晰', '逆袭热血', '阶段爆发', '阅读顺滑'],
    forbidden: ['避免升级体系混乱', '避免爽点来得太突然缺少铺垫', '避免主角长期被动无成长反馈'],
    toneExample: '当那股力量自气海深处暴涌而出时，先前所有轻蔑的目光，都在这一刻化为了惊骇。'
  },
  {
    id: 'web_wochi_xihongshi',
    category: '网文作者',
    name: '我吃西红柿派',
    description: '节奏稳、结构清楚，长于成长主线、修炼体系、目标驱动与正向反馈，阅读体验流畅。',
    features: ['结构清楚', '成长稳健', '目标驱动', '反馈明确'],
    forbidden: ['避免结构混乱', '避免支线喧宾夺主', '避免情节长时间原地踏步'],
    toneExample: '他很清楚，想要走得更远，眼前这一步就绝不能退。唯有跨过去，才能看到更高处的风景。'
  },
  {
    id: 'web_ergen',
    category: '网文作者',
    name: '耳根派',
    description: '兼具修真成长、宿命感、孤独感与哲思气质，擅长把人物心境和世界规则结合起来。',
    features: ['修真宿命', '心境描写', '孤独感', '哲思意味'],
    forbidden: ['避免纯爽文式无代价升级', '避免人物心境完全空白', '避免修真世界缺少命运感与规则感'],
    toneExample: '他站在风里，忽然明白这一路失去的，不只是故人，还有那个曾经会回头张望的自己。'
  },
  {
    id: 'web_tangjia_sanshao',
    category: '网文作者',
    name: '唐家三少派',
    description: '强调少年热血、团队羁绊、成长试炼与正向情感驱动，适合明亮型长线成长故事。',
    features: ['少年热血', '团队羁绊', '成长试炼', '情感正向'],
    forbidden: ['避免整体基调过于阴郁沉重', '避免团队关系缺少互动与情感支撑', '避免成长线只有力量没有精神成长'],
    toneExample: '少年攥紧了拳，眼里的光却比星辰更亮，因为他知道，自己从来不是一个人在战斗。'
  }
]

export const styleStrengthOptions = [
  { id: 'light', name: '轻度' },
  { id: 'medium', name: '中度' },
  { id: 'strong', name: '强烈' }
]

export const authorStyleGroups = authorStyles.reduce((groups, style) => {
  const category = style.category || '其他'
  if (!groups[category]) groups[category] = []
  groups[category].push(style)
  return groups
}, {})

export const authorStyleMap = Object.fromEntries(authorStyles.map(style => [
  style.id,
  {
    mode: 'manual',
    style_id: style.id,
    name: style.name,
    description: style.description,
    features: style.features,
    forbidden: style.forbidden,
    tone_example: style.toneExample,
    strength: 'medium'
  }
]))
