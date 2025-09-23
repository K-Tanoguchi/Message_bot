# worker.py (新規作成)
import os
import pytz
import psycopg2
from datetime import datetime
from dotenv import load_dotenv
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi, TextMessage, PushMessageRequest
)

# --- 初期設定 ---
load_dotenv()
channel_access_token = os.getenv('CHANNEL_ACCESS_TOKEN')
DATABASE_URL = os.getenv('DATABASE_URL')
configuration = Configuration(access_token=channel_access_token)
api_client = ApiClient(configuration)
line_bot_api = MessagingApi(api_client)
jst = pytz.timezone('Asia/Tokyo')

def check_and_send_reminders():
    conn = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # 現在時刻になったリマインドを取得
        now = datetime.now(jst)
        cur.execute("SELECT id, target_id, message FROM reminders WHERE send_at <= %s", (now,))
        reminders = cur.fetchall()
        
        if not reminders:
            print(f"{now}: 送信するリマインドはありません。")
            return

        for reminder in reminders:
            r_id, target_id, message = reminder
            print(f"{now}: メッセージを送信します -> {target_id}: {message}")
            
            # メッセージを送信
            push_request = PushMessageRequest(to=target_id, messages=[TextMessage(text=message)])
            line_bot_api.push_message(push_request)
            
            # 送信済みなのでDBから削除
            cur.execute("DELETE FROM reminders WHERE id = %s", (r_id,))
        
        conn.commit()
        
    except Exception as e:
        print(f"エラーが発生しました: {e}")
    finally:
        if conn:
            cur.close()
            conn.close()

if __name__ == '__main__':
    check_and_send_reminders()