import os
import pytz
from datetime import datetime
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

# --- 初期設定 ---

# .envファイルから環境変数を読み込む
load_dotenv()

# Flaskアプリの初期化とLINE Bot情報の取得
app = Flask(__name__)
channel_secret = os.environ.get('LINE_CHANNEL_SECRET')
channel_access_token = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
target_group_id = os.getenv('TARGET_GROUP_ID')

# LINE APIとWebhookハンドラの設定
handler = WebhookHandler(channel_secret)
configuration = Configuration(access_token=channel_access_token)
api_client = ApiClient(configuration)
line_bot_api = MessagingApi(api_client)

# スケジューラーの設定（日本時間）
jst = pytz.timezone('Asia/Tokyo')
scheduler = BackgroundScheduler(daemon=True, timezone=jst)
scheduler.start()


# --- 関数定義 ---

def send_scheduled_push_message(group_id, message_text):
    """予約された時間にグループへメッセージを送信する関数"""
    try:
        message = TextMessage(text=message_text)
        push_request = PushMessageRequest(to=group_id, messages=[message])
        line_bot_api.push_message(push_request)
        print(f"グループ({group_id})へのメッセージ送信に成功しました。")
    except Exception as e:
        print(f"エラー: メッセージ送信に失敗しました: {e}")

# --- Webサーバーの処理 ---

@app.route("/callback", methods=['POST'])
def callback():
    """LINEプラットフォームからのWebhookを処理する"""
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

    # "あとで HH:MM メッセージ" の形式かチェック
    if user_message.startswith("あとで "):
        try:
            # メッセージを分解
            parts = user_message.split(' ', 2)
            time_str = parts[1]
            message_to_send = parts[2]
            
            # 時間をパース
            hour, minute = map(int, time_str.split(':'))

            # 実行日時を計算
            now = datetime.now(jst)
            run_date = now.replace(hour=hour, minute=minute, second=0, microsecond=0)

            # もし指定時間が過去なら、明日の同じ時間にセット
            if run_date < now:
                run_date = run_date + timedelta(days=1)

            # スケジュールにタスクを追加
            scheduler.add_job(
                send_scheduled_push_message,
                'date',
                run_date=run_date,
                args=[target_group_id, message_to_send]
            )
            
            reply_text = f"承知しました。\n{run_date.strftime('%H:%M')}にグループへ「{message_to_send}」と送信します。"
            
        except (IndexError, ValueError):
            reply_text = "フォーマットが正しくありません。\n「あとで HH:MM メッセージ内容」の形式で送信してください。"
    else:
        # "あとで"で始まらないメッセージは無視
        return

    # ユーザーに予約完了などを返信
    reply_request = ReplyMessageRequest(
        reply_token=reply_token,
        messages=[TextMessage(text=reply_text)]
    )
    line_bot_api.reply_message(reply_request)


# --- プログラムの実行 ---

if __name__ == "__main__":
    # Renderなどの本番環境では、Gunicornなどがこのファイルを実行します
    # 手元で動かす場合は、以下の行のコメントを外してください
    app.run(port=5000, debug=True)
    pass