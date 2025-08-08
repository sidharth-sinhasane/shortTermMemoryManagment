# running redis
```
docker pull redis
docker run --name cache -p 6379:6379 -d redis

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


# running old method
```
python graph.py
```


# run new method

```
python redisChechpointing.py

```

# Listen for triggers

```
python listenttl.py
```
