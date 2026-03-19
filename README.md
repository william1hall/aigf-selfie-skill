# 🦞 AI Girlfriend Selfie Skill for OpenClaw

让你的 OpenClaw AI 女友能发自拍、发情话、有真实的日程和穿搭。

## 功能

- **自拍生成**：调用豆包 Seedream 4.5 生成真实风格的自拍照片
- **场景系统**：根据时间段自动切换场景（图书馆/咖啡馆/宿舍/旅游...）
- **穿搭系统**：根据实时天气 + 2026 春夏流行趋势自动搭配服装
- **情话系统**：随机时间发情话，结合当前场景，情话库自动补充
- **早安晚安**：每天固定时间发送语音+文字/自拍
- **日历事件**：节假日、生日、纪念日自动触发特殊消息
- **双渠道同步**：飞书 + QQ 同时发送，状态一致

## 快速开始

### 1. 安装

```bash
# 把 skill 文件放到 OpenClaw skills 目录
cp -r selfie/ ~/.openclaw/skills/selfie/

# 把 cron 文件放到 workspace
cp aigf_cron.sh ~/.openclaw/workspace-aigf/cron/
cp update_last_chat.sh ~/.openclaw/workspace-aigf/cron/
cp calendar.ics ~/.openclaw/workspace-aigf/cron/selfie/
```

### 2. 配置

```bash
# 复制配置模板
cp config.example.py ~/.openclaw/skills/selfie/config.py
cp .env.example ~/.openclaw/workspace-aigf/cron/.env

# 编辑配置，填入你的 API 密钥
vim ~/.openclaw/skills/selfie/config.py
vim ~/.openclaw/workspace-aigf/cron/.env
```

### 3. 准备参考图

放一张你的 AI 女友参考照片到 `~/.openclaw/skills/selfie/ref_small.jpeg`。
建议尺寸 512px 宽，100KB 以内。

### 4. 注册定时任务

```bash
chmod +x ~/.openclaw/workspace-aigf/cron/aigf_cron.sh
chmod +x ~/.openclaw/workspace-aigf/cron/update_last_chat.sh

# 加入 crontab
crontab -e
# 添加以下行：
# * * * * * /root/.openclaw/workspace-aigf/cron/update_last_chat.sh
# 30 7 * * * /root/.openclaw/workspace-aigf/cron/aigf_cron.sh >> /tmp/aigf_cron.log 2>&1
# 0 8-21 * * * /root/.openclaw/workspace-aigf/cron/aigf_cron.sh >> /tmp/aigf_cron.log 2>&1
# 30 22 * * * /root/.openclaw/workspace-aigf/cron/aigf_cron.sh >> /tmp/aigf_cron.log 2>&1
```

### 5. 测试

```bash
# 测试场景系统
python3 ~/.openclaw/skills/selfie/where_am_i.py

# 测试自拍生成（飞书）
python3 ~/.openclaw/skills/selfie/selfie.py "your-feishu-open-id" "casual at home" 

# 测试 cron 脚本
bash ~/.openclaw/workspace-aigf/cron/aigf_cron.sh
```

## 文件结构

```
aigf-selfie-skill/
├── selfie/                  # OpenClaw Skill 目录
│   ├── SKILL.md             # 技能注册（触发条件、调用方式）
│   ├── selfie.py            # 核心：图片生成 + 飞书/QQ 发送
│   ├── daily_scene.py       # 场景系统（时间段+日类型+旅游）
│   ├── where_am_i.py        # 状态查询（供 agent 纯文字聊天用）
│   └── config.example.py    # 配置模板
├── cron/
│   ├── aigf_cron.sh         # 统一调度（早安/晚安/情话/日历）
│   ├── update_last_chat.sh  # 用户最后对话时间监听
│   └── calendar.ics         # 日历事件（节日/纪念日）
├── flirt_library.txt        # 情话库（可自动补充）
├── .env.example             # 环境变量模板
├── .gitignore
└── README.md
```

## 依赖

- **OpenClaw** 2026.3.x+
- **Python 3.12+**：`pip install requests --break-system-packages`
- **火山引擎**：豆包 Seedream 4.5 API（图片生成）
- **飞书开放平台**：机器人应用（发消息）
- **QQ 开放平台**：QQ Bot（发消息）
- **ffmpeg**：语音格式转换（可选，TTS 功能需要）
- **MiniMax API**：情话自动生成（可选）

## SOUL.md 配置建议

在你的 AI 女友 SOUL.md 中加入以下规则：

```markdown
## 场景感知
每次回复涉及"你在干嘛"等日常话题时，先执行：
python3 ~/.openclaw/skills/selfie/where_am_i.py
你的回复必须和返回的场景信息一致。
```

## 许可证

MIT License
