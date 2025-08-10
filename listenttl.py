import redis


def on_key_expired(primary, secondary, key):
    try:
        json_value = secondary.execute_command('JSON.GET', key)

        if key.startswith("checkpoint:"):
            print("########################## inside on_key_expired#################")
            print(f"[Trigger] Key expired: {key}, value: {json_value}")

        
        secondary.delete(key)

    
    except Exception as e:
        print(f"[Trigger] Key expired: {key}, error getting JSON value from secondary: {e}")

def on_key_added(primary, secondary, key):
    print("########################## inside on_key_added#################")
    try:
        dumped = primary.dump(key)
        if dumped is not None:
            # Copy to secondary without TTL (permanent until manually deleted)
            secondary.restore(key, 0, dumped)
            print(f"[Trigger] Copied key to secondary: {key}")
        else:
            print(f"[Trigger] Failed to dump key: {key}")
    except Exception as e:
        print(f"[Trigger] Error copying key {key} to secondary: {e}")

def on_key_deleted(secondary, key):
    print("########################## inside on_key_deleted#################")
    secondary.delete(key)
    print(f"[Trigger] Deleted key from secondary: {key}")


def check_redis_config(client):
    print("########################## inside check_redis_config#################")
    """Check Redis keyspace notification configuration"""
    try:
        config = client.config_get("notify-keyspace-events")
        print(f"Current Redis notify-keyspace-events config: {config}")
        
        # Enable comprehensive keyspace notifications
        client.config_set("notify-keyspace-events", "KEA")
        print("Set notify-keyspace-events to KEA (all events)")
        
        # Verify the change
        new_config = client.config_get("notify-keyspace-events")
        print(f"Updated Redis notify-keyspace-events config: {new_config}")
        
    except Exception as e:
        print(f"Error checking/setting Redis config: {e}")

def listen_for_all_events():
    print("########################## inside listen_for_all_events#################")
    """Listen for both new keys and expired keys"""
    primary = redis.StrictRedis(host="localhost", port=6379, db=0)
    secondary = redis.StrictRedis(host="localhost", port=6380, db=0)
    pubsub = primary.pubsub()
    
    # Check and set Redis configuration for primary
    check_redis_config(primary)
    
    # Subscribe to multiple events
    patterns = [
        "__keyevent@0__:set",          # SET command
        "__keyevent@0__:mset",         # MSET command
        "__keyevent@0__:hset",         # Hash SET
        "__keyevent@0__:lpush",        # List operations
        "__keyevent@0__:rpush",        # List operations
        "__keyevent@0__:sadd",         # Set operations
        "__keyevent@0__:zadd",         # Sorted set operations
        "__keyevent@0__:json.set",     # JSON operations
        "__keyevent@0__:expired",      # Expired keys
        "__keyevent@0__:del",          # Deleted keys
        "__keyevent@0__:evicted",      # Evicted keys
    ]
    
    for pattern in patterns:
        pubsub.psubscribe(pattern)
        print(f"Subscribed to: {pattern}")
    
    print("\nListening for all key events...")

    for message in pubsub.listen():
        if message["type"] == "pmessage":
            pattern = message["pattern"].decode()
            event_type = pattern.split(":")[-1]
            key = message["data"].decode()
            
            print(f"[DEBUG] Pattern: {pattern}, Event: {event_type}, Key: {key}")
            
            if event_type in ["set", "mset", "hset", "lpush", "rpush", "sadd", "zadd", "json.set"]:
                on_key_added(primary, secondary, key)
            elif event_type == "expired":
                on_key_expired(primary, secondary, key)
            elif event_type in ["del", "evicted"]:
                on_key_deleted(secondary, key)

if __name__ == "__main__":
    listen_for_all_events()