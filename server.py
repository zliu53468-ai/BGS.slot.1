import os
from fastapi import FastAPI, Request
from linebot import LineBotApi, WebhookHandler
from linebot.models import (
    TextSendMessage,
    MessageEvent,
    TextMessage,
    FollowEvent
)
from slot_engine import SlotEngine

app = FastAPI()

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

user_engines = {}

@app.get("/")
def home():
    return {"status": "slot analysis bot running"}

@app.post("/webhook")
async def webhook(req: Request):
    body = await req.body()
    signature = req.headers.get("X-Line-Signature")
    handler.handle(body.decode(), signature)
    return "OK"


@handler.add(FollowEvent)
def handle_follow(event):
    text = (
        "🎰 老虎機數據分析系統\n\n"
        "輸入格式：下注,贏分,是否BONUS\n"
        "例：10,0,0"
    )
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=text)
    )


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    user_msg = event.message.text.strip()

    if user_id not in user_engines:
        user_engines[user_id] = SlotEngine()

    engine = user_engines[user_id]

    try:
        bet, win, bonus = user_msg.split(",")
        bet = float(bet)
        win = float(win)
        bonus = bool(int(bonus))

        engine.add_spin(bet, win, bonus)
        result = engine.analyze()

        reply = (
            f"📊 轉數:{result['total_spins']}\n"
            f"RTP:{result['rtp_score']} | EMA:{result['ema_rtp']}\n"
            f"波動:{result['volatility']} | Gap:{result['bonus_gap']}\n\n"
            f"🔥 {result['mode']}\n"
            f"➡ 建議下注:{result['next_bet']}\n"
            f"➡ 建議轉數:{result['next_spins']}"
        )

    except:
        reply = "格式錯誤，請輸入：下注,贏分,是否BONUS"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )
