"""Basic connection example.
"""

import redis

r = redis.Redis(
    host='redis-17350.c8.us-east-1-3.ec2.redns.redis-cloud.com',
    port=17350,
    decode_responses=True,
    username="default",
    password="QZV0dLghz0lX93ZS8CbKohpCBi7qU9Br",
)

success = r.set('foo', 'bar')
# True

result = r.get('foo')
print(result)
# >>> bar

