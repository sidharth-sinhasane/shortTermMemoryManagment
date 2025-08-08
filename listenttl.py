import redis

def on_key_expired(key):
    print(f"[Trigger] Key expired: {key}")

def listen_for_expiry():
    client = redis.StrictRedis(host="localhost", port=6379, db=0)
    pubsub = client.pubsub()
    pubsub.psubscribe("__keyevent@0__:expired")
    print("Listening for expired keys...")

    for message in pubsub.listen():
        if message["type"] == "pmessage":
            expired_key = message["data"].decode()
            on_key_expired(expired_key)

if __name__ == "__main__":
    listen_for_expiry()
