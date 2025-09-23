import os
import pytz
from datetime import datetime, timedelta
from dotenv import load_dotenv
from flask import Flask, request, abort

from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi, TextMessage,
    PushMessageRequest, ReplyMessageRequest
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from apscheduler.schedulers.background import BackgroundScheduler
import json

# --- 初期設定 ---
load_dotenv()
app = Flask(__name__)
channel_secret = os.getenv('CHANNEL_SECRET')
channel_access_token = os.getenv('CHANNEL_ACCESS_TOKEN')
# ★ 送信先のグループIDを読み込む
target_group_id = os.getenv('TARGET_GROUP_ID')

handler = WebhookHandler(channel_secret)
configuration = Configuration(access_token=channel_access_token)
api_client = ApiClient(configuration)
line_bot_api = MessagingApi(api_client)

# --- スケジューラーの設定 ---
jst = pytz.timezone('Asia/Tokyo')
scheduler = BackgroundScheduler(daemon=True, timezone=jst)
scheduler.start()
print("########### スケジューラーを起動しました ###########")


# --- 関数定義 ---
# ★ 関数名をわかりやすく変更
def send_message_to_group(group_id, message_text):
    """予約された時間にグループへメッセージを送信する関数"""
     # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
    # この関数が呼び出されたことを確認するためのログを追加
    print("####### スケジュールされたタスクが実行されました！ #######")
    print(f"送信先グループID: {group_id}")
    print(f"送信メッセージ: {message_text}")
    # ★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★★
    try:
        message = TextMessage(text=message_text)
        push_request = PushMessageRequest(to=group_id, messages=[message])
        line_bot_api.push_message(push_request)
        print(f"グループ({group_id})へのメッセージ送信に成功しました。")
    except Exception as e:
        print(f"エラー: グループへのメッセージ送信に失敗しました: {e}")

# --- Webサーバーの処理 ---
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    """ユーザーからのメッセージを処理する"""
    user_message = event.message.text
    reply_token = event.reply_token
    reply_text = ""

    # "リマインド HH:MM メッセージ" の形式かチェック
    if user_message.startswith("リマインド "):
        try:
            parts = user_message.split(' ', 2)
            time_str = parts[1]
            message_to_send = parts[2]
            hour, minute = map(int, time_str.split(':'))

            now = datetime.now(jst)
            run_date = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

            if run_date < now:
                run_date = run_date + timedelta(days=1)

            # ★ スケジュールにジョブを追加する際、送信先を target_group_id に変更
            scheduler.add_job(
                send_message_to_group,
                'date',
                run_date=run_date,
                args=[target_group_id, message_to_send]
            )
            
            # ★ 返信メッセージを修正
            reply_text = f"承知しました。\n{run_date.strftime('%m月%d日 %H:%M')}にグループへ「{message_to_send}」と送信します。"
            
        except (IndexError, ValueError):
            reply_text = "フォーマットが正しくありません。\n「リマインド HH:MM メッセージ内容」の形式で送信してください。"
    else:
        return

    reply_request = ReplyMessageRequest(reply_token=reply_token, messages=[TextMessage(text=reply_text)])
    line_bot_api.reply_message(reply_request)


# --- プログラムの実行 ---
if __name__ == "__main__":
    app.run(port=5000, debug=False)