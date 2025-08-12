import redis

# Connect to your Redis server
r = redis.Redis(
    host='localhost',
    port=6379,
    decode_responses=True
)

modules = r.execute_command("MODULE", "LIST")
print(modules)