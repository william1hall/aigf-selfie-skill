#!/bin/bash
# update_last_chat.sh - 监听飞书+QQ消息，更新统一的用户最后对话时间
# crontab: * * * * * /path/to/update_last_chat.sh

LAST_USER_CHAT_FILE="${AIGF_WORKSPACE:-/root/.openclaw/workspace-aigf}/memory/last_user_chat.txt"
AGENT_NAME="${AIGF_AGENT:-aigf}"

# 找最新的 session 文件
LATEST_SESSION=$(ls -t /root/.openclaw/agents/$AGENT_NAME/sessions/*.jsonl 2>/dev/null | head -1)
[ -z "$LATEST_SESSION" ] && exit 0

LAST_USER_TS=$(python3 -c "
import json, datetime
last_ts = 0
with open('$LATEST_SESSION') as f:
    for line in f:
        try:
            d = json.loads(line)
            msg = d.get('message', {})
            if msg.get('role') == 'user':
                ts = msg.get('timestamp', 0) or d.get('timestamp', 0)
                if ts > last_ts: last_ts = ts
        except: pass
if last_ts > 0:
    print(datetime.datetime.fromtimestamp(last_ts / 1000).strftime('%Y-%m-%d %H:%M:%S'))
" 2>/dev/null)

if [ -n "$LAST_USER_TS" ]; then
    if [ -f "$LAST_USER_CHAT_FILE" ]; then
        CURRENT_SEC=$(date -d "$(cat "$LAST_USER_CHAT_FILE")" +%s 2>/dev/null || echo "0")
        NEW_SEC=$(date -d "$LAST_USER_TS" +%s 2>/dev/null || echo "0")
        [ $NEW_SEC -gt $CURRENT_SEC ] && echo "$LAST_USER_TS" > "$LAST_USER_CHAT_FILE"
    else
        mkdir -p "$(dirname "$LAST_USER_CHAT_FILE")"
        echo "$LAST_USER_TS" > "$LAST_USER_CHAT_FILE"
    fi
fi
