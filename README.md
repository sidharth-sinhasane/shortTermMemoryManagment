# running redis
```
docker pull redis
docker run -d --name redis-server -p 6379:6379 redis
docker run -d --name redis-copy -p 6380:6379 redis

```


# create venv

```
python -m venv venv
source venv/bin/activate
```

# install dependencies 

```
pip install -r requirements.txt
```

# create .env
and add api keys


# running old method
```
python graph.py
```


# run new method

```
python redisChechpointing.py

```

# Listen for triggers

if trigger is not created 

start cli
```
docker exec -it cache redis-cli
```

run 
```
redis-cli CONFIG SET notify-keyspace-events Exg
```

```
python listenttl.py
```
