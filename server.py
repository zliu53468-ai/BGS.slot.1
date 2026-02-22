import os
import sys
from fastapi import FastAPI, Request, HTTPException
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import TextSendMessage, MessageEvent, TextMessage, FollowEvent
from slot_engine import SlotEngine

# =============================
# 環境變數讀取
# =============================

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_CHANNEL_SECRET:
    print("❌ LINE 環境變數未設定")
    sys.exit(1)

# =============================
# 初始化
# =============================

app = FastAPI()

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

user_engines = {}

# =============================
# 健康檢查
# =============================

@app.get("/")
def health():
    return {"status": "slot bot running"}

# =============================
# Webhook Endpoint
# =============================

@app.post("/webhook")
async def webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("X-Line-Signature")

    # 🔥 允許 Verify 測試（沒有 signature 也回 200）
    if signature:
        try:
            handler.handle(body.decode("utf-8"), signature)
        except InvalidSignatureError:
            raise HTTPException(status_code=400, detail="Invalid Signature")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    return "OK"

# =============================
# Follow 事件
# =============================

@handler.add(FollowEvent)
def handle_follow(event):
    welcome_text = (
        "🎰 老虎機數據分析系統 🎰\n\n"
        "請輸入格式：\n"
        "下注 贏分 是否BONUS\n\n"
        "範例：\n"
        "100 0 0\n"
        "100 500 1"
    )

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=welcome_text)
    )

# =============================
# 訊息事件
# =============================

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    user_msg = event.message.text.strip()

    if user_id not in user_engines:
        user_engines[user_id] = SlotEngine()

    engine = user_engines[user_id]

    try:
        parts = user_msg.split()
        if len(parts) != 3:
            raise ValueError

        bet = float(parts[0])
        win = float(parts[1])
        bonus = bool(int(parts[2]))

        engine.add_spin(bet, win, bonus)
        result = engine.analyze()

        reply = (
            f"📊 轉數:{result['total_spins']}\n"
            f"RTP30:{result['rtp30']} | RTP50:{result['rtp50']} | RTP100:{result['rtp100']}\n"
            f"BONUS間距:{result['bonus_gap']} 轉\n"
            f"大獎密度:{result['big_win_density']}"
        )

    except:
        reply = "⚠️ 格式錯誤\n請輸入：下注 贏分 是否BONUS\n例：100 0 0"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )
