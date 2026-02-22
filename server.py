import os
import sys
from fastapi import FastAPI, Request
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    TextSendMessage,
    MessageEvent,
    TextMessage,
    FollowEvent,
    QuickReply,
    QuickReplyButton,
    MessageAction
)
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

GAMES = {
    "1": "RSG 雷神之鎚 V1",
    "2": "RSG 雷神之鎚 V2",
    "3": "ATG 戰神塞特 V1",
    "4": "ATG 戰神塞特 V2",
    "5": "QT 仙境傳說",
    "6": "QT 月兔",
    "7": "QT 奢華"
}

# =============================
# 健康檢查
# =============================

@app.get("/")
def home():
    return {"status": "slot analysis bot running"}

# =============================
# Webhook
# =============================

@app.post("/webhook")
async def webhook(req: Request):
    body = await req.body()
    signature = req.headers.get("X-Line-Signature")
    body_text = body.decode("utf-8")

    if body_text == '{"events":[]}':
        return "OK"

    if not signature:
        return "OK"

    try:
        handler.handle(body_text, signature)
    except InvalidSignatureError:
        print("Invalid Signature")
    except Exception as e:
        print("Webhook Error:", str(e))

    return "OK"

# =============================
# Follow（加入按鈕）
# =============================

@handler.add(FollowEvent)
def handle_follow(event):
    welcome_text = (
        "🎰 歡迎使用老虎機數據分析系統 🎰\n\n"
        "請點擊下方按鈕開始使用"
    )

    quick_reply = QuickReply(items=[
        QuickReplyButton(
            action=MessageAction(label="開始使用 🎮", text="start")
        )
    ])

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(
            text=welcome_text,
            quick_reply=quick_reply
        )
    )

# =============================
# 訊息處理
# =============================

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    user_msg = event.message.text.strip()

    if user_id not in user_engines:
        user_engines[user_id] = SlotEngine(bankroll=10000)

    engine = user_engines[user_id]

    # ===== start =====
    if user_msg.lower() == "start":
        menu = "🎮 請選擇遊戲：\n\n"
        for k, v in GAMES.items():
            menu += f"{k}. {v}\n"

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=menu)
        )
        return

    # ===== 選遊戲 =====
    if user_msg in GAMES:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text=f"已選擇：{GAMES[user_msg]}\n請開始輸入數據"
            )
        )
        return

    # ===== 分析輸入 =====
    try:
        bet, win, bonus = user_msg.split()

        bet = float(bet)
        win = float(win)
        bonus = bool(int(bonus))

        engine.add_spin(bet, win, bonus)
        result = engine.analyze()

        reply = (
            f"📊 數據分析結果\n\n"
            f"🎯 總轉數：{result['total_spins']}\n"
            f"💰 當前餘額：{result['balance']}\n"
            f"📈 RTP：{result['rtp']}\n"
            f"🌊 波動：{result['volatility']}\n"
            f"🎁 BONUS間距：{result['bonus_gap']} 轉\n\n"
            f"🔥 模式：{result['mode']}\n"
            f"➡ 建議下注：{result['next_bet']}\n"
            f"➡ 建議轉數：{result['next_spins']}\n"
            f"{result['stop']}"
        )

    except Exception:
        reply = (
            "⚠️ 格式錯誤，請輸入：下注 贏分 是否BONUS\n"
            "例如：10 0 0"
        )

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )

# =============================
# 本地啟動
# =============================

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 10000))
    uvicorn.run("server:app", host="0.0.0.0", port=port)
