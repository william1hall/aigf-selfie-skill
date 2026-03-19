"""
AI 女友自拍技能 - 配置文件模板

使用方法：
1. 复制此文件为 config.py
2. 填入你自己的 API 密钥和用户 ID
"""
import os

# ─── 火山引擎 / 豆包 ──────────────────────────────────────
IMAGE_MODEL = "doubao-seedream-4-5-250815"  # 或你自己创建的 endpoint ID
VOLC_API_KEY = os.environ.get("VOLC_API_KEY", "your-volcengine-api-key")

# ─── 参考图（人设基准照，建议压缩到 100KB 以内）────────────
REFERENCE_IMAGE_URL = ""  # 可选，留空则用本地路径
REFERENCE_IMAGE_PATH = os.path.join(os.path.dirname(__file__), "ref_small.jpeg")

# ─── 图片风格 prompt 后缀 ─────────────────────────────────
PHOTO_STYLE = "high quality, realistic photography, natural skin texture, soft lighting"

# ─── 飞书 ────────────────────────────────────────────────────
FEISHU_APP_ID = os.environ.get("FEISHU_APP_ID", "your-feishu-app-id")
FEISHU_APP_SECRET = os.environ.get("FEISHU_APP_SECRET", "your-feishu-app-secret")

# ─── 服务器公网 IP（QQ 图片中转用）──────────────────────────
SERVER_IP = os.environ.get("SERVER_IP", "your-server-public-ip")
SERVER_PORT = int(os.environ.get("SERVER_PORT", "8080"))
