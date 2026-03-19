"""
daily_scene.py — 周浩薇的每日场景状态系统 v2

核心设计：
- 每天早上第一次调用时，决定今天是什么"日类型"（工作日/周末/节假日）
- 日类型决定一天的基调：正常上课 vs 旅游 vs 运动 vs 宅家 vs 逛上海
- 一天分成时间段，同一时间段内场景固定（飞书/QQ共享）
- 节假日概率：50%外地旅游 / 10%上海周边逛 / 10%宅家 / 30%运动
"""

import os
import json
import random
import datetime

SCENE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "daily_scene.json")
DAY_PLAN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "daily_plan.json")

# ═══════════════════════════════════════════════════════════
# 节假日判断
# ═══════════════════════════════════════════════════════════

HOLIDAYS_2026 = [
    ("2026-01-01", "2026-01-03"),
    ("2026-01-26", "2026-02-01"),
    ("2026-04-04", "2026-04-06"),
    ("2026-05-01", "2026-05-05"),
    ("2026-06-17", "2026-06-19"),
    ("2026-10-01", "2026-10-08"),
]

def is_holiday(date: datetime.date) -> bool:
    ds = date.strftime("%Y-%m-%d")
    for start, end in HOLIDAYS_2026:
        if start <= ds <= end:
            return True
    return False

def is_free_day(date: datetime.date) -> bool:
    return date.weekday() >= 5 or is_holiday(date)

# ═══════════════════════════════════════════════════════════
# 旅游目的地
# ═══════════════════════════════════════════════════════════

TRAVEL_DESTINATIONS = [
    {"dest": "杭州西湖", "scenes": {
        "morning_activity": "walking along Su Causeway by West Lake, spring scenery, natural morning light",
        "afternoon_activity": "sitting in lakeside tea house near West Lake, drinking Longjing tea, warm afternoon light",
        "dinner_time": "walking through Hefang Street night market, lively atmosphere, warm street lights",
    }},
    {"dest": "南京", "scenes": {
        "morning_activity": "walking in front of Sun Yat-sen Mausoleum, grand stairway, morning sunlight through trees",
        "afternoon_activity": "exploring Confucius Temple area, traditional architecture, warm afternoon light",
        "dinner_time": "eating at restaurant near Qinhuai River, cozy warm indoor lighting",
    }},
    {"dest": "苏州", "scenes": {
        "morning_activity": "walking in Humble Administrator Garden, classical Chinese garden, morning mist, peaceful pond",
        "afternoon_activity": "strolling along Pingjiang Road, white-walled houses by canal, afternoon sun",
        "dinner_time": "having dinner near Shantang Street, warm lantern lights, canal view",
    }},
    {"dest": "乌镇", "scenes": {
        "morning_activity": "walking on stone bridge in Wuzhen water town, morning mist over canal",
        "afternoon_activity": "sitting in riverside teahouse in Wuzhen, warm afternoon light, boats on canal",
        "dinner_time": "dinner at waterside restaurant, warm lantern reflections on water",
    }},
    {"dest": "黄山", "scenes": {
        "morning_activity": "hiking on mountain trail, pine trees and misty peaks, fresh morning air",
        "afternoon_activity": "resting at scenic viewpoint, panoramic mountain view, afternoon clouds below",
        "dinner_time": "having hot pot at mountain lodge, warm cozy interior, tired but happy",
    }},
]

# ═══════════════════════════════════════════════════════════
# 上海本地游
# ═══════════════════════════════════════════════════════════

SHANGHAI_LOCAL = {
    "morning_activity": [
        {"scene_en": "walking along the Bund waterfront, Huangpu River morning view, iconic skyline background", "location_cn": "外滩"},
        {"scene_en": "browsing vintage shops in Tianzifang alley, artsy vibe, warm morning light", "location_cn": "田子坊"},
    ],
    "afternoon_activity": [
        {"scene_en": "having afternoon tea at cafe in French Concession, tree-lined street view, warm cozy interior", "location_cn": "法租界咖啡馆"},
        {"scene_en": "window shopping on Nanjing Road, vibrant commercial street, bright day", "location_cn": "南京路"},
        {"scene_en": "visiting Shanghai Museum exhibition, modern art display, bright gallery lighting", "location_cn": "上海博物馆"},
    ],
    "dinner_time": [
        {"scene_en": "having dinner at restaurant with Lujiazui skyline night view, warm ambient lighting", "location_cn": "陆家嘴"},
        {"scene_en": "eating xiaolongbao at famous restaurant, warm steamy atmosphere", "location_cn": "南翔小笼店"},
    ],
}

# ═══════════════════════════════════════════════════════════
# 运动场景
# ═══════════════════════════════════════════════════════════

SPORT_SCENES = {
    "morning_activity": [
        {"scene_en": "jogging in university sports field, energetic pose, morning sunlight, light sweat", "location_cn": "学校操场"},
        {"scene_en": "doing yoga on exercise mat in gym, focused calm expression, bright indoor lighting", "location_cn": "健身房"},
        {"scene_en": "swimming in university pool, poolside selfie, wet hair, bright blue water", "location_cn": "游泳馆"},
    ],
    "afternoon_activity": [
        {"scene_en": "playing badminton in sports hall, energetic action, bright indoor lighting", "location_cn": "体育馆"},
        {"scene_en": "working out at gym, using treadmill, energetic smile, gym mirrors background", "location_cn": "健身房"},
        {"scene_en": "doing pilates in studio, stretching pose, natural light, calm atmosphere", "location_cn": "瑜伽工作室"},
    ],
    "dinner_time": [
        {"scene_en": "relaxing at smoothie bar after workout, healthy drink in hand, casual tired smile", "location_cn": "轻食店"},
    ],
}

# ═══════════════════════════════════════════════════════════
# 宅家场景
# ═══════════════════════════════════════════════════════════

HOME_SCENES = {
    "morning_activity": [
        {"scene_en": "sitting on sofa watching morning drama, cozy blanket, warm living room light, relaxed", "location_cn": "宿舍"},
        {"scene_en": "sitting at desk doing online shopping on laptop, casual relaxed morning, warm room", "location_cn": "宿舍"},
    ],
    "afternoon_activity": [
        {"scene_en": "lying on bed reading novel, afternoon sunlight through curtains, peaceful lazy vibe", "location_cn": "宿舍"},
        {"scene_en": "baking cookies in small kitchen, flour on hands, warm oven light, happy smile", "location_cn": "宿舍小厨房"},
    ],
    "dinner_time": [
        {"scene_en": "ordering takeout, sitting on bed with food boxes, watching show on laptop, cozy room", "location_cn": "宿舍"},
    ],
}

# ═══════════════════════════════════════════════════════════
# 工作日场景
# ═══════════════════════════════════════════════════════════

NORMAL_SCENES = {
    "sleeping": [
        {"scene_en": "sleeping in bed, eyes closed, peaceful, soft pillow, dim bedroom lighting", "location_cn": "宿舍卧室"},
        {"scene_en": "sleeping in bed, hugging pillow, cozy blanket, dark room with faint moonlight", "location_cn": "宿舍卧室"},
    ],
    "morning_routine": [
        {"scene_en": "just woke up, messy hair, standing in front of bathroom mirror, morning sunlight", "location_cn": "宿舍"},
        {"scene_en": "just woke up, sitting on bed, stretching, morning sunlight through curtains", "location_cn": "宿舍"},
    ],
    "morning_activity": [
        {"scene_en": "sitting in university library by the window, studying with laptop, natural morning light, books on desk", "location_cn": "学校图书馆"},
        {"scene_en": "sitting at desk in psychology research lab, working on computer, bright office lighting", "location_cn": "心理学实验室"},
        {"scene_en": "sitting in university lecture hall, taking notes, natural light from large windows", "location_cn": "教室"},
    ],
    "lunch_break": [
        {"scene_en": "sitting in university canteen, eating lunch, casual and relaxed, bright indoor lighting", "location_cn": "学校食堂"},
        {"scene_en": "sitting in small cafe near campus, having light lunch, warm cozy interior", "location_cn": "校门口的咖啡馆"},
        {"scene_en": "lying on dorm bed taking a short nap after lunch, cozy afternoon light", "location_cn": "宿舍"},
    ],
    "afternoon_activity": [
        {"scene_en": "sitting in university library, reading research papers, focused, afternoon sunlight through windows", "location_cn": "学校图书馆"},
        {"scene_en": "sitting in cozy cafe, working on laptop with coffee, warm afternoon light, bokeh background", "location_cn": "咖啡馆"},
        {"scene_en": "in psychology lab, organizing experiment data on computer, focused expression, bright lighting", "location_cn": "心理学实验室"},
    ],
    "dinner_time": [
        {"scene_en": "sitting at restaurant table, having dinner, warm indoor lighting, relaxed smile", "location_cn": "餐厅"},
        {"scene_en": "walking on campus path after dinner, evening golden hour light, relaxed stroll", "location_cn": "校园里"},
        {"scene_en": "in university canteen having dinner, lively atmosphere, warm lighting", "location_cn": "学校食堂"},
    ],
    "evening_activity": [
        {"scene_en": "sitting at dorm desk, working on laptop, warm desk lamp lighting, cozy room", "location_cn": "宿舍"},
        {"scene_en": "in library evening self-study session, quiet atmosphere, warm indoor lighting", "location_cn": "图书馆"},
        {"scene_en": "sitting on dorm bed watching drama on laptop, relaxed, warm room lighting", "location_cn": "宿舍"},
    ],
    "night_relaxing": [
        {"scene_en": "sitting on bed scrolling phone, relaxed look, soft warm bedside lamp", "location_cn": "宿舍"},
        {"scene_en": "sitting at desk doing skincare routine, mirror on desk, warm soft lighting", "location_cn": "宿舍"},
        {"scene_en": "lying on bed chatting on phone, cozy room, warm ambient lighting", "location_cn": "宿舍"},
    ],
}

# ═══════════════════════════════════════════════════════════
# 日计划
# ═══════════════════════════════════════════════════════════

def get_daily_plan() -> dict:
    today = datetime.date.today().strftime("%Y-%m-%d")

    if os.path.exists(DAY_PLAN_FILE):
        try:
            with open(DAY_PLAN_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("date") == today:
                    return data
        except (json.JSONDecodeError, KeyError):
            pass

    date_obj = datetime.date.today()

    if is_free_day(date_obj):
        roll = random.random()
        if roll < 0.50:
            dest = random.choice(TRAVEL_DESTINATIONS)
            plan = {"date": today, "day_type": "travel", "travel_dest": dest["dest"], "travel_scenes": dest["scenes"]}
        elif roll < 0.60:
            plan = {"date": today, "day_type": "shanghai_local"}
        elif roll < 0.70:
            plan = {"date": today, "day_type": "home"}
        else:
            plan = {"date": today, "day_type": "sport"}
    else:
        plan = {"date": today, "day_type": "normal"}

    with open(DAY_PLAN_FILE, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)

    return plan

# ═══════════════════════════════════════════════════════════
# 时间段
# ═══════════════════════════════════════════════════════════

def get_time_slot(hour: int, minute: int = 0) -> str:
    t = hour * 60 + minute
    if t < 420:       return "sleeping"
    elif t < 510:     return "morning_routine"
    elif t < 720:     return "morning_activity"
    elif t < 810:     return "lunch_break"
    elif t < 1050:    return "afternoon_activity"
    elif t < 1140:    return "dinner_time"
    elif t < 1320:    return "evening_activity"
    elif t < 1410:    return "night_relaxing"
    else:             return "sleeping"

# ═══════════════════════════════════════════════════════════
# 核心接口
# ═══════════════════════════════════════════════════════════

def get_current_scene() -> dict:
    now = datetime.datetime.now()
    today = now.strftime("%Y-%m-%d")
    current_slot = get_time_slot(now.hour, now.minute)

    if os.path.exists(SCENE_FILE):
        try:
            with open(SCENE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("date") == today and data.get("slot") == current_slot:
                    return data
        except (json.JSONDecodeError, KeyError):
            pass

    plan = get_daily_plan()
    day_type = plan["day_type"]

    # 通用时间段不受日类型影响
    universal_slots = ["sleeping", "morning_routine", "lunch_break", "evening_activity", "night_relaxing"]

    scene = None

    if current_slot in universal_slots:
        pool = NORMAL_SCENES.get(current_slot, NORMAL_SCENES["evening_activity"])
        scene = random.choice(pool)

    elif day_type == "travel":
        travel_scenes = plan.get("travel_scenes", {})
        if current_slot in travel_scenes:
            scene = {"scene_en": travel_scenes[current_slot], "location_cn": plan["travel_dest"]}
        else:
            pool = NORMAL_SCENES.get(current_slot, NORMAL_SCENES["evening_activity"])
            scene = random.choice(pool)

    elif day_type == "shanghai_local":
        local = SHANGHAI_LOCAL.get(current_slot)
        scene = random.choice(local) if local else random.choice(NORMAL_SCENES.get(current_slot, NORMAL_SCENES["evening_activity"]))

    elif day_type == "sport":
        sport = SPORT_SCENES.get(current_slot)
        scene = random.choice(sport) if sport else random.choice(NORMAL_SCENES.get(current_slot, NORMAL_SCENES["evening_activity"]))

    elif day_type == "home":
        home = HOME_SCENES.get(current_slot)
        scene = random.choice(home) if home else random.choice(NORMAL_SCENES.get(current_slot, NORMAL_SCENES["evening_activity"]))

    else:
        pool = NORMAL_SCENES.get(current_slot, NORMAL_SCENES["evening_activity"])
        scene = random.choice(pool)

    result = {
        "date": today,
        "slot": current_slot,
        "day_type": day_type,
        "scene_en": scene["scene_en"],
        "location_cn": scene.get("location_cn", "未知"),
        "travel_dest": plan.get("travel_dest", ""),
        "generated_at": now.strftime("%H:%M"),
    }

    with open(SCENE_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    return result


# ═══════════════════════════════════════════════════════════
# 动态细节层：同一地点，不同姿势/表情/视角
# ═══════════════════════════════════════════════════════════

RANDOM_POSES = [
    "looking directly at camera with a gentle smile",
    "glancing sideways with a playful smirk",
    "resting chin on one hand, looking at camera",
    "tucking hair behind ear, soft smile",
    "looking down at phone then glancing up at camera",
    "leaning forward slightly, cheerful expression",
    "tilting head to one side, cute expression",
    "making a peace sign near face, bright smile",
    "holding a drink close to face, peeking over it",
    "laughing naturally with eyes slightly squinting",
    "pouting lips slightly, cute selfie angle",
    "stretching arms up, relaxed happy expression",
    "waving at camera, friendly warm smile",
    "biting lower lip slightly, shy cute look",
    "resting head on folded arms on desk, looking up at camera",
]

RANDOM_ANGLES = [
    "shot from slightly above, flattering selfie angle",
    "straight-on close-up selfie",
    "slightly tilted camera angle, casual vibe",
    "medium shot showing upper body and surroundings",
    "close-up face selfie with blurred background",
]

RANDOM_DETAILS = [
    "a strand of hair falling across face",
    "soft natural light highlighting cheekbones",
    "steam rising from a hot drink nearby",
    "earphones dangling around neck",
    "a small hair clip on one side",
    "glasses pushed up on forehead",
    "a scrunchie on wrist",
    "a tiny sticker on phone case visible in mirror",
    "a cute keychain hanging from bag in background",
    "a half-eaten snack on the table nearby",
    "pen tucked behind ear",
    "messy notes scattered on desk behind",
]


def get_scene_for_selfie(agent_scene_prompt: str = "", travel_dest: str = "") -> str:
    if travel_dest:
        return agent_scene_prompt

    current = get_current_scene()
    base_scene = current["scene_en"]

    # 每次调用追加随机的动态细节，让同一地点拍出不同照片
    pose = random.choice(RANDOM_POSES)
    angle = random.choice(RANDOM_ANGLES)
    detail = random.choice(RANDOM_DETAILS)

    dynamic_scene = f"{base_scene}, {pose}, {angle}, {detail}"

    return dynamic_scene


if __name__ == "__main__":
    plan = get_daily_plan()
    print(f"今日计划: {plan['day_type']}")
    if plan.get("travel_dest"):
        print(f"旅游目的地: {plan['travel_dest']}")
    scene = get_current_scene()
    print(f"时间段: {scene['slot']}")
    print(f"场景: {scene['scene_en']}")
    print(f"地点: {scene['location_cn']}")
