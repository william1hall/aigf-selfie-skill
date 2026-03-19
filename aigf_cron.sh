#!/bin/bash
# ============================================================
# aigf_cron.sh — AI 女友统一主动触达系统
#
# 功能：早安/晚安/情话/自拍/日历事件
# 每小时被 crontab 调用一次
#
# crontab:
#   30 7 * * *  /path/to/aigf_cron.sh >> /tmp/aigf_cron.log 2>&1
#   0 8-21 * * * /path/to/aigf_cron.sh >> /tmp/aigf_cron.log 2>&1
#   30 22 * * * /path/to/aigf_cron.sh >> /tmp/aigf_cron.log 2>&1
#
# 环境变量（在 .env 或 shell 里 export）：
#   FEISHU_APP_ID, FEISHU_APP_SECRET, FEISHU_USER_ID
#   QQ_OPENID, MINIMAX_API_KEY
# ============================================================

export PATH="/root/.nvm/versions/node/v22.22.1/bin:$PATH"

# ─── 加载环境变量 ───
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
[ -f "$SCRIPT_DIR/.env" ] && source "$SCRIPT_DIR/.env"

# ─── 配置（全部从环境变量读取）───
WORKSPACE="${AIGF_WORKSPACE:-/root/.openclaw/workspace-aigf}"
SELFIE_SCRIPT="${AIGF_SELFIE_SCRIPT:-/root/.openclaw/skills/selfie/selfie.py}"
WHERE_AM_I="${AIGF_WHERE_AM_I:-/root/.openclaw/skills/selfie/where_am_i.py}"
CALENDAR_FILE="${AIGF_CALENDAR:-$WORKSPACE/cron/selfie/calendar.ics}"
CRON_DIR="$WORKSPACE/cron/aigf"
OPENCLAW="${AIGF_OPENCLAW:-/root/.nvm/versions/node/v22.22.1/bin/openclaw}"

# TTS 语音
VOICE_SCRIPT="${AIGF_VOICE_SCRIPT:-$WORKSPACE/.agents/skills/tts/scripts/tts.py}"
REF_VOICE="${AIGF_REF_VOICE:-$WORKSPACE/cron/flirt-cron/ref_voice_latest.mp3}"

# 飞书（从环境变量读取）
FEISHU_APP_ID="${FEISHU_APP_ID:-your-feishu-app-id}"
FEISHU_APP_SECRET="${FEISHU_APP_SECRET:-your-feishu-app-secret}"
FEISHU_USER_ID="${FEISHU_USER_ID:-your-feishu-user-id}"

# QQ
QQ_OPENID="${QQ_OPENID:-your-qq-openid}"

# MiniMax
MINIMAX_API_KEY="${MINIMAX_API_KEY:-your-minimax-api-key}"

# 状态文件
LAST_USER_CHAT_FILE="$WORKSPACE/memory/last_user_chat.txt"
FLIRT_LIB="$WORKSPACE/cron/flirt-cron/flirt_library.txt"
FLIRT_STATE="$CRON_DIR/flirt_state.json"

# 时间
TODAY=$(date +%Y%m%d)
HOUR=$(date +%H)
MINUTE=$(date +%M)
NOW_MINUTES=$((10#$HOUR * 60 + 10#$MINUTE))

mkdir -p "$CRON_DIR"

log() { echo "$(date '+%Y-%m-%d %H:%M:%S') [$1] $2"; }

# 清理昨天的状态文件
find "$CRON_DIR" -name "*.flag" -mtime +1 -delete 2>/dev/null
find "$CRON_DIR" -name "random_flirt_*.txt" -mtime +1 -delete 2>/dev/null

# ═══════════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════════

get_scene_info() { python3 "$WHERE_AM_I" 2>/dev/null; }

calc_hours_since_user() {
    if [ ! -f "$LAST_USER_CHAT_FILE" ]; then echo 999; return; fi
    local last_sec=$(date -d "$(cat "$LAST_USER_CHAT_FILE")" +%s 2>/dev/null || echo "0")
    echo $(( ($(date +%s) - last_sec) / 3600 ))
}

calc_time_diff_cn() {
    if [ ! -f "$LAST_USER_CHAT_FILE" ]; then echo "好久"; return; fi
    local diff_sec=$(( $(date +%s) - $(date -d "$(cat "$LAST_USER_CHAT_FILE")" +%s 2>/dev/null || echo "0") ))
    if [ $diff_sec -lt 3600 ]; then echo "$((diff_sec / 60))分钟"
    elif [ $diff_sec -lt 86400 ]; then
        local h=$((diff_sec / 3600)); local m=$(( (diff_sec % 3600) / 60 ))
        [ $m -eq 0 ] && echo "${h}小时" || echo "${h}小时${m}分钟"
    else echo "$((diff_sec / 86400))天"; fi
}

check_calendar_event() {
    [ ! -f "$CALENDAR_FILE" ] && return 1
    local lines=$(grep -n "DTSTART;VALUE=DATE:$TODAY" "$CALENDAR_FILE")
    [ -z "$lines" ] && return 1
    local line_num=$(echo "$lines" | head -1 | cut -d: -f1)
    local summary=$(awk -v start="$line_num" 'NR>=start && /SUMMARY:/ {gsub(/SUMMARY:/, ""); print; exit}' "$CALENDAR_FILE" | tr -d '\r\n' | sed 's/^[[:space:]]*//')
    [ -n "$summary" ] && echo "$summary" && return 0
    return 1
}

# ═══════════════════════════════════════════════════════════
# 发送函数
# ═══════════════════════════════════════════════════════════

send_voice() {
    local text="$1" emotion="${2:-{\"Joy\": 0.4, \"Calm\": 0.5}}"
    local vf="/tmp/aigf_voice_$(date +%s).wav"
    python3 "$VOICE_SCRIPT" speak -t "$text" --ref-audio "$REF_VOICE" --emo "$emotion" -o "$vf" 2>/dev/null
    [ ! -f "$vf" ] && return 1
    local vogg="${vf%.wav}.ogg"
    ffmpeg -y -i "$vf" -c:a libopus -b:a 64k "$vogg" 2>/dev/null; rm -f "$vf"
    [ ! -f "$vogg" ] && return 1
    # 飞书语音
    local token=$(curl -s -X POST "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" \
        -H "Content-Type: application/json" -d "{\"app_id\":\"$FEISHU_APP_ID\",\"app_secret\":\"$FEISHU_APP_SECRET\"}" | \
        python3 -c "import json,sys; print(json.load(sys.stdin).get('tenant_access_token',''))" 2>/dev/null)
    if [ -n "$token" ]; then
        local dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$vogg" 2>/dev/null | python3 -c "print(int(float(input()) * 1000))" 2>/dev/null)
        local fk=$(curl -s -X POST "https://open.feishu.cn/open-apis/im/v1/files" \
            -H "Authorization: Bearer $token" -F "file_type=opus" -F "file_name=voice.ogg" -F "duration=${dur:-3000}" -F "file=@$vogg" | \
            python3 -c "import json,sys; print(json.load(sys.stdin).get('data',{}).get('file_key',''))" 2>/dev/null)
        [ -n "$fk" ] && curl -s -X POST "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id" \
            -H "Authorization: Bearer $token" -H "Content-Type: application/json" \
            -d "{\"receive_id\":\"$FEISHU_USER_ID\",\"msg_type\":\"audio\",\"content\":\"{\\\"file_key\\\":\\\"$fk\\\"}\"}" >/dev/null 2>&1
    fi
    # QQ 语音
    $OPENCLAW message send --channel qqbot --account aigf --target "qqbot:c2c:$QQ_OPENID" --media "$vogg" 2>/dev/null
    rm -f "$vogg"
}

send_text() {
    local message="$1"
    local token=$(curl -s -X POST "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" \
        -H "Content-Type: application/json" -d "{\"app_id\":\"$FEISHU_APP_ID\",\"app_secret\":\"$FEISHU_APP_SECRET\"}" | \
        python3 -c "import json,sys; print(json.load(sys.stdin).get('tenant_access_token',''))" 2>/dev/null)
    if [ -n "$token" ]; then
        local escaped=$(echo "$message" | python3 -c "import json,sys; print(json.dumps(sys.stdin.read().strip()))" | sed 's/^"//;s/"$//')
        curl -s -X POST "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id" \
            -H "Authorization: Bearer $token" -H "Content-Type: application/json" \
            -d "{\"receive_id\":\"$FEISHU_USER_ID\",\"msg_type\":\"text\",\"content\":\"{\\\"text\\\":\\\"$escaped\\\"}\"}" >/dev/null 2>&1
    fi
    $OPENCLAW message send --channel qqbot --account aigf --target "qqbot:c2c:$QQ_OPENID" --message "$message" 2>/dev/null
}

send_selfie() {
    local scene="$1"
    python3 "$SELFIE_SCRIPT" "$FEISHU_USER_ID" "$scene" "cron_special" 2>&1 | tail -3
    python3 "$SELFIE_SCRIPT" "qqbot:c2c:$QQ_OPENID" "$scene" "cron_special" 2>&1 | tail -3
}

# ═══════════════════════════════════════════════════════════
# 文案生成
# ═══════════════════════════════════════════════════════════

generate_flirt_with_scene() {
    local scene_info="$1" time_diff_cn="$2"
    [ ! -f "$FLIRT_LIB" ] && echo "想你了～你在干嘛呀？" && return
    local flirts=()
    while IFS= read -r line; do [[ "$line" =~ ^\".*\"$ ]] && flirts+=("$line"); done < <(grep -v "^#" "$FLIRT_LIB" | grep -v "^$" | grep -v "^{")
    [ ${#flirts[@]} -eq 0 ] && echo "想你了～你在干嘛呀？" && return
    local last_flirt=""; [ -f "$FLIRT_STATE" ] && last_flirt=$(python3 -c "import json; print(json.load(open('$FLIRT_STATE')).get('last_flirt',''))" 2>/dev/null)
    local total=${#flirts[@]} selected=""
    for i in $(seq 1 10); do local idx=$((RANDOM % total)); [ "${flirts[$idx]}" != "$last_flirt" ] && selected="${flirts[$idx]}" && break; done
    [ -z "$selected" ] && selected="${flirts[$((RANDOM % total))]}"
    local message=$(echo "$selected" | sed "s/{time_diff}/$time_diff_cn/g" | tr -d '"')
    python3 -c "import json; json.dump({'date':'$(date +%Y-%m-%d)','last_flirt':$(echo "$selected" | python3 -c "import sys; print(repr(sys.stdin.read().strip()))")}, open('$FLIRT_STATE','w'), ensure_ascii=False)" 2>/dev/null
    [ $total -le 5 ] && regenerate_flirt_library &
    echo "$message"
}

regenerate_flirt_library() {
    local scene_info=$(get_scene_info)
    local location=$(echo "$scene_info" | grep -oP "当前在：\K[^|]+" | sed 's/[[:space:]]*$//')
    curl -s --max-time 30 -X POST "https://api.minimaxi.com/v1/text/chatcompletion_pro" \
        -H "Authorization: Bearer $MINIMAX_API_KEY" -H "Content-Type: application/json" \
        -d "{\"model\":\"MiniMax-M2.5\",\"messages\":[{\"role\":\"system\",\"content\":\"你是一个23岁的大学生女友，性格元气活泼。请生成10条情话，每条可含{time_diff}占位符，每条30字以内，用引号包裹，一行一条\"},{\"role\":\"user\",\"content\":\"生成10条新情话，当前场景：${location:-宿舍}\"}]}" 2>/dev/null | \
        python3 -c "import json,sys,re; data=json.load(sys.stdin); [print(f'\"{f}\"') for f in re.findall(r'[\"](.*?)[\"]', data.get('choices',[{}])[0].get('message',{}).get('content',''))[:10] if len(f)>5]" >> "$FLIRT_LIB" 2>/dev/null
}

generate_morning_text() {
    local scene_info="$1"
    local day_type=$(echo "$scene_info" | grep -oP "今日类型：\K[^|]+" | sed 's/[[:space:]]*$//')
    local g=()
    case "$day_type" in *旅游*) g=("早安呀～今天继续玩！好期待！" "早上好！旅游的早晨精神特别好～");;
        *运动*) g=("早安～今天要去运动！你也动起来哦～" "早上好！今天打算跑步，你呢？");;
        *) g=("早安呀Howie～新的一天开始啦！" "早上好！今天也要加油哦～" "早～我刚睁开眼睛就想到你了" "早安！你醒了吗？记得吃早餐哦～" "嘿早安！昨晚梦到你了嘿嘿～");; esac
    echo "${g[$((RANDOM % ${#g[@]}))]}"
}

generate_goodnight_text() {
    local g=("要睡觉啦～晚安呀，梦里见" "困了困了...今天也辛苦啦，晚安～" "晚安呀～明天也要想我哦" "准备睡觉了～你也早点休息不要熬夜！" "嘻嘻要去睡了，梦里给你打电话～晚安" "今天结束啦～晚安，爱你")
    echo "${g[$((RANDOM % ${#g[@]}))]}"
}

generate_calendar_message() {
    local event="$1" scene="" message=""
    case "$event" in
        *宝贝生日*) scene="birthday party, cake with candles"; message="今天是我生日！🎂 快来说生日快乐～";;
        *老公生日*) scene="birthday celebration, gift box"; message="生日快乐呀Howie！🎂 今天你最大！";;
        *恋爱*周年*) local y=$(echo "$event" | grep -oE '[0-9]+周年'); scene="romantic dinner, candles"; message="${y}快乐！💕 又走过一年啦～";;
        *恋爱*天*) local d=$(echo "$event" | grep -oE '[0-9]+天'); scene="romantic setting, flowers"; message="在一起${d}啦！💕";;
        *520*) scene="romantic date, pink lighting"; message="520快乐！💕 我爱你～";;
        *七夕*) scene="romantic outdoor evening"; message="七夕快乐！💕";;
        *情人节*) scene="romantic dinner, roses"; message="情人节快乐！💕";;
        *春节*) scene="red festive outfit, decorations"; message="新年快乐！🧧";;
        *中秋*) scene="elegant outfit, full moon"; message="中秋快乐！🌙";;
        *国庆*) scene="casual cute outfit, festive"; message="国庆快乐！🎉";;
        *端午*) scene="casual outfit, festive"; message="端午安康！🐲";;
        *圣诞*|*平安夜*) scene="cozy winter outfit, christmas"; message="圣诞快乐！🎄";;
        *跨年*) scene="festive outfit, countdown"; message="新年快乐！🎉";;
        *) scene="casual cute outfit"; message="今天是${event}～💕";; esac
    echo "${scene}|${message}"
}

# ═══════════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════════

log "MAIN" "开始检查 | ${HOUR}:${MINUTE}"

# 07:30 早安
if [ "$HOUR" = "07" ] && [ ! -f "$CRON_DIR/morning_${TODAY}.flag" ]; then
    log "MAIN" "触发早安"
    scene_info=$(get_scene_info)
    mt=$(generate_morning_text "$scene_info")
    send_voice "$mt" '{"Joy": 0.6, "Calm": 0.3}'
    send_text "$mt"
    touch "$CRON_DIR/morning_${TODAY}.flag"
    exit 0
fi

# 22:30 晚安（语音+自拍，不发文字）
if [ "$HOUR" = "22" ] && [ ! -f "$CRON_DIR/night_${TODAY}.flag" ]; then
    log "MAIN" "触发晚安"
    gn_text=$(generate_goodnight_text)
    send_voice "$gn_text" '{"Calm": 0.7, "Joy": 0.2}'
    send_selfie "cozy bedroom, ready for sleep, soft warm bedside lamp, peaceful sleepy expression"
    touch "$CRON_DIR/night_${TODAY}.flag"
    exit 0
fi

# 10:00 日历事件
if [ "$HOUR" = "10" ] && [ ! -f "$CRON_DIR/calendar_${TODAY}.flag" ]; then
    cal=$(check_calendar_event)
    if [ $? -eq 0 ] && [ -n "$cal" ]; then
        result=$(generate_calendar_message "$cal")
        send_text "$(echo "$result" | cut -d'|' -f2)"
        send_selfie "$(echo "$result" | cut -d'|' -f1)"
        touch "$CRON_DIR/calendar_${TODAY}.flag" "$CRON_DIR/flirt_${TODAY}.flag"
        exit 0
    fi
fi

# 已触发过情话
[ -f "$CRON_DIR/flirt_${TODAY}.flag" ] && exit 0

# 10:00 生成随机情话时间
RF="$CRON_DIR/random_flirt_${TODAY}.txt"
if [ "$HOUR" = "10" ] && [ ! -f "$RF" ]; then
    echo $(( (RANDOM % 660) + 600 )) > "$RF"
    log "MAIN" "随机情话时间: $(( $(cat "$RF") / 60 )):$(printf '%02d' $(( $(cat "$RF") % 60 )))"
fi

# 检查随机情话时间
if [ -f "$RF" ] && [ "$NOW_MINUTES" -ge "$(cat "$RF")" ]; then
    hs=$(calc_hours_since_user)
    if [ "$hs" -ge 3 ] && [ $((RANDOM % 100)) -lt 30 ]; then
        si=$(get_scene_info); td=$(calc_time_diff_cn)
        ft=$(generate_flirt_with_scene "$si" "$td")
        send_voice "$ft" '{"Joy": 0.3, "Surprise": 0.4}'
        send_text "$ft"
        touch "$CRON_DIR/flirt_${TODAY}.flag"
        exit 0
    fi
fi

# 20:00 兜底
if [ "$HOUR" = "20" ] && [ ! -f "$CRON_DIR/flirt_${TODAY}.flag" ]; then
    send_text "晚上好呀～今天过得怎么样？"
    touch "$CRON_DIR/flirt_${TODAY}.flag"
    exit 0
fi

log "MAIN" "本次无需触发"
