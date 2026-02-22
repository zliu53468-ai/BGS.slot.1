import os
import sys
from fastapi import FastAPI, Request
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    TextSendMessage,
    MessageEvent,
    TextMessage,
    FollowEvent
)
from slot_engine import SlotEngine

LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

if not LINE_CHANNEL_ACCESS_TOKEN or not LINE_CHANNEL_SECRET:
    print("❌ LINE 環境變數未設定")
    sys.exit(1)

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

@app.get("/")
def home():
    return {"status": "slot analysis bot running"}

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

@handler.add(FollowEvent)
def handle_follow(event):
    welcome_text = (
        "🎰 歡迎使用老虎機數據分析系統 🎰\n\n"
        "請先設定本金：\n"
        "例如：本金 10000"
    )

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=welcome_text)
    )

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):

    user_id = event.source.user_id
    if not user_id:
        return

    user_msg = event.message.text.strip()

    if user_msg == "結束分析":
        if user_id in user_engines:
            del user_engines[user_id]
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="✅ 已結束分析，模型已停止。\n如需重新開始請輸入：本金 10000")
        )
        return

    # ===== 本金設定 =====
    if user_id not in user_engines:

        try:
            bankroll = None

            if user_msg.startswith("本金"):
                amount = user_msg.replace("本金", "").strip()
                bankroll = float(amount)

            elif user_msg.replace(".", "", 1).isdigit():
                bankroll = float(user_msg)

            if bankroll is not None:
                user_engines[user_id] = SlotEngine(bankroll=bankroll)
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=f"💰 本金設定完成：{bankroll}\n請輸入 start 開始分析")
                )
                return

        except:
            pass

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="⚠️ 請先設定本金，例如：本金 10000")
        )
        return

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
            TextSendMessage(
                text=(
                    f"已選擇：{GAMES[user_msg]}\n"
                    "請開始輸入數據\n\n"
                    "例如：\n"
                    "30 500\n\n"
                    "30 = 本局下注金額\n"
                    "500 = 本局贏分"
                )
            )
        )
        return

    # ===== 分析輸入 =====
    try:
        bet, win = user_msg.split()
        bet = float(bet)
        win = float(win)

        engine.add_spin(bet, win)
        result = engine.analyze()

        reply = (
            f"📊 數據分析結果\n\n"
            f"🎯 總轉數：{result['total_spins']}\n"
            f"💰 當前餘額：{result['balance']}\n"
            f"📈 RTP：{result['rtp']}\n\n"
            f"🔥 模式：{result['mode']}\n"
            f"➡ 建議下注：{result['next_bet']}\n"
            f"➡ 建議轉數：{result['next_spins']}\n"
            f"{result['stop']}"
        )

        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply)
        )

    except:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(
                text="⚠️ 格式錯誤，請輸入：下注 贏分\n例如：30 500"
            )
        )

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 10000))
    uvicorn.run("server:app", host="0.0.0.0", port=port)
