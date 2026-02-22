import os
import sys
from fastapi import FastAPI, Request, HTTPException
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import TextSendMessage, MessageEvent, TextMessage, FollowEvent
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

@app.get("/")
def health():
    return {"status": "slot bot running"}

@app.post("/webhook")
async def webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("X-Line-Signature")

    if not signature:
        raise HTTPException(status_code=400, detail="Missing Signature")

    try:
        handler.handle(body.decode("utf-8"), signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid Signature")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    return "OK"

@handler.add(FollowEvent)
def handle_follow(event):
    text = "🎰 請先設定本金：\n例如：本金 10000"
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=text))

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    msg = event.message.text.strip()

    # ===== 設定本金（改為空格格式）=====
    if msg.startswith("本金"):
        try:
            _, amount = msg.split()
            bankroll = float(amount)
            user_engines[user_id] = SlotEngine(bankroll)

            reply = f"✅ 本金設定完成：{bankroll}\n請開始輸入：下注 贏分 是否BONUS\n例如：100 0 0"
        except:
            reply = "格式錯誤，例如：本金 10000"

        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
        return

    if user_id not in user_engines:
        reply = "請先設定本金，例如：本金 10000"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
        return

    engine = user_engines[user_id]

    try:
        # ===== 改為用空格切割 =====
        bet, win, bonus = msg.split()
        bet = float(bet)
        win = float(win)
        bonus = bool(int(bonus))

        engine.add_spin(bet, win, bonus)
        result = engine.analyze()

        reply = (
            f"📊 轉數:{result['total_spins']}｜餘額:{result['balance']}\n"
            f"RTP:{result['rtp']}｜波動:{result['volatility']}｜Gap:{result['bonus_gap']}\n\n"
            f"🔥 {result['mode']}\n"
            f"➡ 建議下注:{result['next_bet']}\n"
            f"➡ 建議轉數:{result['next_spins']}\n"
            f"{result['stop']}"
        )

    except:
        reply = "格式錯誤，請輸入：下注 贏分 是否BONUS\n例如：100 0 0"

    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 10000))
    uvicorn.run("server:app", host="0.0.0.0", port=port)
