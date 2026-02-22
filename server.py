import os
import sys
from fastapi import FastAPI, Request, HTTPException
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    TextSendMessage,
    MessageEvent,
    TextMessage,
    FollowEvent
)
from slot_engine import SlotEngine

# =============================
# 環境變數
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

# 每位使用者獨立分析引擎
user_engines = {}

# 遊戲館分類
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
# Webhook（穩定版）
# =============================

@app.post("/webhook")
async def webhook(req: Request):
    body = await req.body()
    signature = req.headers.get("X-Line-Signature")
    body_text = body.decode("utf-8")

    # 🔥 LINE Verify 會送空 events
    if body_text == '{"events":[]}':
        return "OK"

    if not signature:
        raise HTTPException(status_code=400, detail="Missing Signature")

    try:
        handler.handle(body_text, signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid Signature")
    except Exception as e:
        print("Webhook Error:", str(e))
        return "OK"

    return "OK"

# =============================
# Follow 事件
# =============================

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

# =============================
# 訊息事件
# =============================

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    user_msg = event.message.text.strip()

    # 初始化使用者引擎
    if user_id not in user_engines:
        user_engines[user_id] = SlotEngine()

    engine = user_engines[user_id]

    # ===== start 選單 =====
    if user_msg.lower() == "start":
        menu = "🎮 請選擇遊戲：\n\n"
        for k, v in GAMES.items():
            menu += f"{k}. {v}\n"

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=menu)
        )
        return

    # ===== 選擇遊戲 =====
    if user_msg in GAMES:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text=f"✅ 已選擇：{GAMES[user_msg]}\n請開始輸入數據"
            )
        )
        return

    # ===== 分析輸入 =====
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

    except Exception:
        reply = (
            "⚠️ 格式錯誤，請輸入：下注,贏分,是否BONUS\n"
            "例如：10,0,0"
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
