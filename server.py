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

# 每位使用者獨立分析引擎
user_engines = {}

GAMES = {
    "1": "RSG 雷神之鎚 V1",
    "2": "RSG 雷神之鎚 V2",
    "3": "ATG 戰神塞特 V1",
    "4": "ATG 戰神塞特 V2",
    "5": "QT 仙境傳說",
    "6": "QT 月兔",
    "7": "QT 奢華"
}

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
    welcome_text = (
        "🎰 歡迎使用老虎機數據分析系統 🎰\n\n"
        "本系統僅提供統計分析與數據觀察。\n\n"
        "📘 使用步驟：\n"
        "1️⃣ 輸入 start 開啟選單\n"
        "2️⃣ 選擇遊戲編號\n"
        "3️⃣ 每一轉輸入：下注,贏分,是否BONUS\n\n"
        "範例：\n"
        "10,0,0\n"
        "10,120,1"
    )

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=welcome_text)
    )


@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    user_msg = event.message.text.strip()

    if user_id not in user_engines:
        user_engines[user_id] = SlotEngine()

    engine = user_engines[user_id]

    if user_msg.lower() == "start":
        menu = "🎮 請選擇遊戲：\n\n"
        for k, v in GAMES.items():
            menu += f"{k}. {v}\n"
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=menu)
        )
        return

    if user_msg in GAMES:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"已選擇：{GAMES[user_msg]}\n請開始輸入數據")
        )
        return

    try:
        bet, win, bonus = user_msg.split(",")
        bet = float(bet)
        win = float(win)
        bonus = bool(int(bonus))

        engine.add_spin(bet, win, bonus)
        result = engine.analyze()

        reply = (
            f"📊 數據分析結果\n\n"
            f"總轉數：{result['total_spins']}\n"
            f"RTP30：{result['rtp30']}\n"
            f"RTP50：{result['rtp50']}\n"
            f"RTP100：{result['rtp100']}\n\n"
            f"BONUS間距：{result['bonus_gap']} 轉\n"
            f"大獎密度：{result['big_win_density']}"
        )

    except:
        reply = "⚠️ 格式錯誤，請輸入：下注,贏分,是否BONUS\n例如：10,0,0"

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )
