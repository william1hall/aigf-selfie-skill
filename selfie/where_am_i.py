#!/usr/bin/env python3
"""
where_am_i.py — 查询周浩薇当前的状态（场景+穿搭）

供 agent 在纯文字聊天时调用，保持场景一致性。
不生成图片，只返回当前状态的文字描述。

用法：
    python3 where_am_i.py

输出示例：
    [STATUS] 时间：下午15:30 | 今日类型：normal | 当前在：学校图书馆 | 穿搭：白T恤+米色风衣+黑色A字短裙配黑丝
"""

import sys
import os
import datetime
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from daily_scene import get_daily_plan, get_current_scene

# 中文时间段名
SLOT_NAMES = {
    "sleeping": "睡觉中",
    "morning_routine": "刚起床",
    "morning_activity": "上午活动",
    "lunch_break": "午饭/午休",
    "afternoon_activity": "下午活动",
    "dinner_time": "晚饭时间",
    "evening_activity": "晚上活动",
    "night_relaxing": "睡前放松",
}

DAY_TYPE_NAMES = {
    "normal": "工作日上课",
    "travel": "出去旅游",
    "shanghai_local": "逛上海",
    "home": "宅家休息",
    "sport": "运动日",
}

# 读取今日穿搭
OUTFIT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "daily_outfit.json")

def get_outfit_cn() -> str:
    """把英文穿搭翻译成简短中文描述"""
    if not os.path.exists(OUTFIT_FILE):
        return "还没决定穿什么"
    try:
        with open(OUTFIT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        parts = []
        if data.get("base"):
            parts.append(data["base"])
        if data.get("outer"):
            parts.append(data["outer"])
        if data.get("bottom"):
            parts.append(data["bottom"])
        if data.get("acc"):
            parts.append(data["acc"])
        return " + ".join(parts) if parts else "休闲装"
    except Exception:
        return "休闲装"


def main():
    now = datetime.datetime.now()
    plan = get_daily_plan()
    scene = get_current_scene()
    outfit = get_outfit_cn()

    time_str = now.strftime("%H:%M")
    slot_cn = SLOT_NAMES.get(scene["slot"], scene["slot"])
    day_type_cn = DAY_TYPE_NAMES.get(plan["day_type"], plan["day_type"])
    location = scene["location_cn"]
    travel = plan.get("travel_dest", "")

    output = f"[STATUS] 时间：{time_str} | 时间段：{slot_cn} | 今日类型：{day_type_cn}"
    if travel:
        output += f" | 旅游目的地：{travel}"
    output += f" | 当前在：{location} | 穿搭：{outfit}"

    print(output)


if __name__ == "__main__":
    main()
