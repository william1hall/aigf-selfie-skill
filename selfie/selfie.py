#!/usr/bin/env python3
"""
selfie.py — AI 女友自拍脚本（豆包 Seededit 3.0 版）

场景由 OpenClaw agent 推断后作为参数传入，
脚本只负责：生成图片 + 发送到飞书/QQ

用法：
    python3 selfie.py "<channel_id>" "<场景英文描述>" [travel_dest] [msg_id]

参数：
    channel_id      飞书 ou_xxx 或 QQ qqbot:c2c:xxx
    场景英文描述     由 agent 生成，如 "sitting in cafe, holding latte"
    travel_dest     可选，旅游目的地，如 "杭州西湖"（有则在图片里强调景点特征）
    msg_id          可选，QQ 触发消息的 msg_id，用于被动回复（不传则主动发送）

示例：
    python3 selfie.py "ou_xxx" "lying on sofa reading book, cozy room, warm lamp"
    python3 selfie.py "qqbot:c2c:xxx" "gym selfie, after workout, energetic" "" "msg_abc123"
    python3 selfie.py "qqbot:c2c:xxx" "standing on Su Causeway" "杭州西湖" "msg_abc123"

依赖：
    pip3 install requests --break-system-packages
"""


import sys, os, time, json, base64, requests, subprocess, threading, uuid
from http.server import HTTPServer, SimpleHTTPRequestHandler
import random
import datetime

# 记事本存放路径
OUTFIT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "daily_outfit.json")

def get_shanghai_temperature():
    """获取上海当前气温（免费免Key的 Open-Meteo API）"""
    try:
        # 经纬度设为上海：31.23, 121.47
        url = "https://api.open-meteo.com/v1/forecast?latitude=31.23&longitude=121.47&current_weather=true"
        r = requests.get(url, timeout=5)
        return float(r.json()["current_weather"]["temperature"])
    except Exception as e:
        print(f"[selfie] ⚠️ 天气获取失败，默认使用 20 度: {e}", flush=True)
        return 20.0  # 如果网络断了，默认 20 度

def get_daily_outfit():
    today = datetime.date.today().strftime("%Y-%m-%d")
    
    # 1. 检查今天是否已经存过衣服
    if os.path.exists(OUTFIT_FILE):
        with open(OUTFIT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if data.get("date") == today:
                return data

    # 2. 如果是新的一天，先看天气
    temp = get_shanghai_temperature()
    print(f"[selfie] 🌡️ 今日上海气温：{temp}℃，正在挑选合适穿搭...", flush=True)
    
    # 3. 根据温度决定衣服池
    if temp < 10:
        # 寒冷：羽绒服/厚外套 + 毛衣
        choices = [
            {"base": "a thick white turtleneck sweater", "outer": "a heavy black winter coat"},
            {"base": "a warm beige knit sweater", "outer": "a white down jacket"}
        ]
    elif temp < 20:
        # 春秋：风衣/牛仔外套 + T恤/薄毛衣
        choices = [
            {"base": "a white tee", "outer": "a beige trench coat"},
            {"base": "a light grey thin sweater", "outer": "a light blue denim jacket"}
        ]
    elif temp < 28:
        # 初夏：开衫 + 短袖
        choices = [
            {"base": "a white short-sleeve t-shirt", "outer": "a thin cotton cardigan"},
            {"base": "a light blue camisole", "outer": "a thin white sun-protection shirt"}
        ]
    else:
        # 炎热：短袖/小裙子（没有外套）
        choices = [
            {"base": "a white short-sleeve t-shirt", "outer": ""},
            {"base": "a light floral summer dress", "outer": ""}
        ]

    chosen_outfit = random.choice(choices)
    chosen_outfit["date"] = today
    
    # 4. 存入记事本
    with open(OUTFIT_FILE, "w", encoding="utf-8") as f:
        json.dump(chosen_outfit, f)
        
    return chosen_outfit

def decide_clothing_prompt(scene_prompt: str, travel_dest: str) -> str:
    scene_lower = scene_prompt.lower()
    
    # 1. 睡觉场景（仅限夜间22点~早上8点）
    hour = datetime.datetime.now().hour
    is_sleep_time = (hour >= 22 or hour < 8)
    if is_sleep_time and any(kw in scene_lower for kw in ["bed", "sleep", "pajama", "woke up", "lying"]):
        return "wearing cute light pink silk pajamas"
        
    daily_outfit = get_daily_outfit()
    
    # 2. 炎热天气没有外套的情况
    if not daily_outfit["outer"]:
        return f"wearing {daily_outfit['base']}"
    
    # 3. 区分室内外
    outdoor_keywords = ["street", "outside", "park", "cafe", "standing", "walking"]
    is_outdoor = travel_dest != "" or any(kw in scene_lower for kw in outdoor_keywords)
    
    if is_outdoor:
        return f"wearing {daily_outfit['base']} and {daily_outfit['outer']}"
    else:
        return f"wearing {daily_outfit['base']}"

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (
    VOLC_API_KEY, REFERENCE_IMAGE_URL, REFERENCE_IMAGE_PATH,
    FEISHU_APP_ID, FEISHU_APP_SECRET,
    IMAGE_MODEL, PHOTO_STYLE
)

VOLC_BASE_URL  = "https://ark.cn-beijing.volces.com/api/v3"
SERVER_IP      = os.environ.get("SERVER_IP", "your-server-ip")
SERVER_PORT    = 8080
SERVE_DIR      = "/tmp/selfie_serve"

def log(msg):
    print(f"[selfie {time.strftime('%H:%M:%S')}] {msg}", flush=True)

# ═══════════════════════════════════════════════════════════
# 渠道判断
# ═══════════════════════════════════════════════════════════

def detect_channel(channel_id: str) -> str:
    return "qq" if channel_id.startswith("qqbot:") else "feishu"

# ═══════════════════════════════════════════════════════════
# 本地 HTTP 中转（QQ 专用）
# ═══════════════════════════════════════════════════════════

def start_file_server():
    os.makedirs(SERVE_DIR, exist_ok=True)

    class QuietHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=SERVE_DIR, **kwargs)
        def log_message(self, format, *args):
            pass

    server = HTTPServer(("0.0.0.0", SERVER_PORT), QuietHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    log(f"🌐 HTTP 文件服务已启动：http://{SERVER_IP}:{SERVER_PORT}/")
    return server

def serve_image_temporarily(image_bytes: bytes) -> tuple[str, str]:
    os.makedirs(SERVE_DIR, exist_ok=True)
    filename = f"{uuid.uuid4().hex}.jpg"
    local_path = os.path.join(SERVE_DIR, filename)
    with open(local_path, "wb") as f:
        f.write(image_bytes)
    public_url = f"http://{SERVER_IP}:{SERVER_PORT}/{filename}"
    return public_url, local_path

# ═══════════════════════════════════════════════════════════
# 编辑图片（豆包 Seededit 3.0），返回图片 URL
# ═══════════════════════════════════════════════════════════

def generate_selfie_image(scene_prompt: str, travel_dest: str = "") -> str:
    location_hint = ""
    if travel_dest:
        location_hint = f"Background clearly shows {travel_dest} landmark scenery. "

    # --- 新增：获取当前的衣服描述 ---
    clothing_desc = decide_clothing_prompt(scene_prompt, travel_dest)

    # --- 修改：把 clothing_desc 塞进 prompt 里强制约束模型 ---
    full_prompt = (
        f"Edit this photo: change the scene, background, and pose to {scene_prompt}. "
        f"{location_hint}"
        f"The person MUST be {clothing_desc}. "  # 强制规定衣服
        f"Strictly maintain the person's facial features, hair, and identity exactly the same. "
        f"{PHOTO_STYLE}."
    )

    log(f"🖼  调用豆包 Seededit 编辑图片...")
    log(f"   场景：{scene_prompt[:60]}...")
    log(f"   今日衣服设定：{clothing_desc}") # 可以在日志里打印出来看看
    
    resp = requests.post(
        f"{VOLC_BASE_URL}/images/generations",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {VOLC_API_KEY}"
        },
        json={
            "model": IMAGE_MODEL,
            "prompt": full_prompt,
            "image": "data:image/jpeg;base64," + base64.b64encode(open(REFERENCE_IMAGE_PATH, "rb").read()).decode(),
            "size": "2k",
            "output_format": "jpeg",
            "watermark": False
        },
        timeout=(10, 300)
    )

    data = resp.json()

    if "error" in data:
        raise RuntimeError(f"API 错误：{data['error']}")

    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code}：{resp.text[:200]}")

    try:
        img_url = data["data"][0]["url"]
    except (KeyError, IndexError):
        raise RuntimeError(f"无法解析返回结构：{json.dumps(data)[:200]}")

    log("✅ 图片编辑成功")
    return img_url

# ═══════════════════════════════════════════════════════════
# 飞书工具（后台子进程下载+上传，主进程快速返回）
# ═══════════════════════════════════════════════════════════

def get_feishu_token() -> str:
    r = requests.post(
        "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
        json={"app_id": FEISHU_APP_ID, "app_secret": FEISHU_APP_SECRET}, timeout=10
    )
    return r.json().get("tenant_access_token", "")

def feishu_send_image_bg(channel_id: str, volc_url: str):
    """后台执行：下载图片并上传飞书，与主进程解耦"""
    try:
        token = get_feishu_token()
        if not token:
            log("❌ [bg] 飞书 token 获取失败"); return

        log("⬇️  [bg] 下载图片...")
        img_resp = requests.get(volc_url, timeout=120)
        if img_resp.status_code != 200:
            log(f"❌ [bg] 图片下载失败 HTTP {img_resp.status_code}"); return
        image_bytes = img_resp.content
        log(f"✅ [bg] 下载完成（{len(image_bytes)} bytes）")

        up = requests.post(
            "https://open.feishu.cn/open-apis/im/v1/images",
            headers={"Authorization": f"Bearer {token}"},
            files={"image": ("selfie.jpeg", image_bytes, "image/jpeg")},
            data={"image_type": "message"}, timeout=60
        )
        key = up.json().get("data", {}).get("image_key", "")
        if not key:
            log(f"❌ [bg] 飞书上传失败：{up.text}"); return
        log(f"✅ [bg] image_key：{key}")

        r = requests.post(
            "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"receive_id": channel_id, "msg_type": "image", "content": f'{{"image_key":"{key}"}}'},
            timeout=10
        )
        if r.json().get("code") == 0:
            log("🎉 [bg] 飞书发送成功！")
        else:
            log(f"❌ [bg] 飞书发送失败：{r.text}")
    except Exception as e:
        log(f"❌ [bg] 异常：{e}")

# ═══════════════════════════════════════════════════════════
# QQ 工具（中转 URL + reply-to）
# ═══════════════════════════════════════════════════════════

def qq_send_image(channel_id: str, img_url: str, msg_id: str = "") -> bool:
    cmd = [
        "openclaw", "message", "send", "--account", "aigf",
        "--channel", "qqbot",
        "--target", channel_id,
        "--media", img_url
    ]
    if msg_id:
        cmd += ["--reply-to", msg_id]
        log(f"📎 被动回复模式，msg_id：{msg_id}")
    else:
        log(f"📤 主动发送模式（无 msg_id）")
    try:
        subprocess.run(cmd, check=True, timeout=30)
        return True
    except subprocess.CalledProcessError as e:
        log(f"❌ QQ 发图失败：{e}"); return False

# ═══════════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════════

def main():
    if len(sys.argv) < 3:
        print("用法：python3 selfie.py \"<channel_id>\" \"<场景英文描述>\" [travel_dest] [msg_id]")
        print("")
        print("示例：")
        print("  python3 selfie.py \"ou_xxx\" \"sitting in cafe, holding latte\"")
        print("  python3 selfie.py \"qqbot:c2c:xxx\" \"casual selfie\" \"\" \"msg_abc123\"")
        print("  python3 selfie.py \"qqbot:c2c:xxx\" \"on Su Causeway\" \"杭州西湖\" \"msg_abc123\"")
        sys.exit(1)

    channel_id   = sys.argv[1]
    channel_id = channel_id.removeprefix("user:")  # 兼容 OpenClaw 传入的 user:ou_xxx 格式
    scene_prompt = sys.argv[2]
    travel_dest  = sys.argv[3] if len(sys.argv) > 3 else ""
    msg_id       = sys.argv[4] if len(sys.argv) > 4 else ""

    ch = detect_channel(channel_id)
    log(f"🚀 开始 | 渠道：{'QQ' if ch == 'qq' else '飞书'} | 旅游地：{travel_dest or '无'} | msg_id：{msg_id or '无'}")

    # 生成图片，返回火山方舟 URL
    try:
        volc_url = generate_selfie_image(scene_prompt, travel_dest)
    except Exception as e:
        log(f"❌ 图片生成失败：{e}")
        print(f"[SELFIE_FAILED] 图片生成失败：{e}")
        sys.exit(1)

    if ch == "feishu":
        # 飞书：后台线程做下载+上传，主进程打印 URL 后立即退出
        # 使用 daemon=False 确保后台线程在主进程退出后继续运行
        t = threading.Thread(
            target=feishu_send_image_bg,
            args=(channel_id, volc_url),
            daemon=False
        )
        t.start()
        log(f"📤 飞书发图已在后台启动，主进程退出")
        print("[SELFIE_SENT_ASYNC] 图片已发送。请用符合人设的语气回复一句简短的配套文字。")

    else:
        # QQ：下载图片到本地，通过 HTTP 中转发送（QQ API 不支持带签名的外部 URL）
        log("⬇️  QQ：下载图片到本地...")
        image_bytes = None
        for attempt in range(3):
            try:
                img_resp = requests.get(volc_url, timeout=180)
                if img_resp.status_code == 200:
                    image_bytes = img_resp.content
                    log(f"✅ 下载完成（{len(image_bytes)} bytes），第 {attempt+1} 次尝试")
                    break
                else:
                    log(f"⚠️ 下载失败 HTTP {img_resp.status_code}，第 {attempt+1} 次尝试")
            except Exception as e:
                log(f"⚠️ 下载异常：{e}，第 {attempt+1} 次尝试")
            time.sleep(3)

        if not image_bytes:
            log("❌ 图片下载彻底失败")
            print("[SELFIE_FAILED] QQ图片下载失败")
            sys.exit(1)

        server = start_file_server()
        public_url, local_path = serve_image_temporarily(image_bytes)
        log(f"🔗 中转 URL：{public_url}")
        time.sleep(1)
        try:
            success = qq_send_image(channel_id, public_url, msg_id)
            log("⏳ 等待 QQ Bot 拉取图片...")
            time.sleep(20)
        finally:
            server.shutdown()
            if os.path.exists(local_path):
                os.remove(local_path)
                log(f"🗑  临时图片已清理")

        if not success:
            log("❌ QQ 发送失败")
            print("[SELFIE_FAILED] QQ发图失败")
            sys.exit(1)
        log("🎉 QQ 发送成功！")
        print("[SELFIE_SENT_ASYNC] 图片已发送。请用符合人设的语气回复一句简短的配套文字。")

if __name__ == "__main__":
    main()
