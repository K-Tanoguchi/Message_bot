import os
import pytz
import psycopg2
from datetime import datetime, timedelta
from dotenv import load_dotenv
from flask import Flask, request, abort

from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi, TextMessage, ReplyMessageRequest
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

# --- 初期設定 ---

# .envファイルから環境変数を読み込む
load_dotenv()

# Flaskアプリの初期化とLINE Bot情報の取得
app = Flask(__name__)
channel_secret = os.getenv('CHANNEL_SECRET')
channel_access_token = os.getenv('CHANNEL_ACCESS_TOKEN')
target_group_id = os.getenv('TARGET_GROUP_ID')
database_url = os.getenv('DATABASE_URL') # データベースURLを読み込む

# LINE APIとWebhookハンドラの設定
handler = WebhookHandler(channel_secret)
configuration = Configuration(access_token=channel_access_token)
api_client = ApiClient(configuration)
line_bot_api = MessagingApi(api_client)
jst = pytz.timezone('Asia/Tokyo')

# --- Webサーバーの処理 ---

@app.route("/")
def health_check():
    """Renderのスリープを防ぐためのヘルスチェック用エンドポイント"""
    return "OK"

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
    """ユーザーからのメッセージを処理し、予約をデータベースに保存する"""
    user_message = event.message.text
    reply_token = event.reply_token
    reply_text = ""

    # "リマインド HH:MM メッセージ" の形式かチェック
    if user_message.startswith("リマインド "):
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

            # データベースに予約を保存
            conn = psycopg2.connect(database_url)
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO reminders (target_id, message, send_at) VALUES (%s, %s, %s)",
                (target_group_id, message_to_send, run_date)
            )
            conn.commit()
            cur.close()
            conn.close()
            
            reply_text = f"承知しました。\n{run_date.strftime('%m月%d日 %H:%M')}にグループへ「{message_to_send}」と送信します。"

        except Exception as e:
            print(f"エラー: {e}")
            reply_text = "予約処理中にエラーが発生しました。"
    else:
        # "リマインド"で始まらないメッセージは何もしない
        return

    # ユーザーに予約完了などを返信
    reply_request = ReplyMessageRequest(
        reply_token=reply_token,
        messages=[TextMessage(text=reply_text)]
    )
    line_bot_api.reply_message(reply_request)

# --- プログラムの実行 ---
if __name__ == "__main__":
    # Renderなどの本番環境ではGunicornが使われるため、この部分は実行されない
    # ローカルでテストする場合は、debug=Trueにして実行する
    app.run(port=5000, debug=True)