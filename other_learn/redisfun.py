import redis

pool = redis.ConnectionPool(host='localhost', port=6379, db=0)
redis = redis.Redis(connection_pool=pool)

redis.set('mykey', 'Hello from Python!')
value = redis.get('mykey')
print(value)

redis.zadd('vehicles', {'car' : 0})
redis.zadd('vehicles', {'bike' : 0})
vehicles = redis.zrange('vehicles', 0, -1)
print(vehicles)

redis.rpush('queue', 'job')
redis.rpush('queue', 'second job')
redis.rpush('queue', 'third job')
for _ in range(redis.llen('queue')):
    print(redis.lpop('queue'))
