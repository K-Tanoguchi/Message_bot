import os

# 環境変数を設定する
#os.environ["LINE_CHANNEL_SECRET"] = "8095e645f79891ba9edbada3450e9fb0"
#os.environ["LINE_CHANNEL_ACCESS_TOKEN"] = "cUCjc/Lk4GXahpVM1qvyV4XAorQPEcJDY4XJkEq1BXhatukBM3hG6pq5zwN6g8W7ObKtVb+LrQZ82v9JsbmvWCm4FlMPgkH95iPo5R2neG1dUa73Fc+ZkdciTXiWvF/p1/xm8A78y8XW04f+kWolYwdB04t89/1O/w1cDnyilFU="
token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
print(token)