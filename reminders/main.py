# convert datetime.utc.now to unix timestamp

import datetime
import time

import redis

REMINDERS = "rs"


def main2():
    r = redis.Redis(host="localhost", port=6379, db=0)
    # record into now variable date of 2000-01-01
    now = datetime.datetime.utcnow()
    future = now + datetime.timedelta(seconds=1)
    unixtime = time.mktime(future.timetuple())
    r.zadd(REMINDERS, {"group_frogs": unixtime})
    while True:
        now = datetime.datetime.utcnow()
        unixtime = time.mktime(now.timetuple())
        print(r.zrevrange(REMINDERS, 0, -1, withscores=True))
        if unixtime >= r.zrevrange(REMINDERS, 0, -1, withscores=True)[0][1]:
            print("It's time to wake up!")
            exit(0)


def main3():
    r = redis.Redis(host="localhost", port=6379, db=0)
    print(r.zrevrange(REMINDERS, 0, -1, withscores=True))


if __name__ == "__main__":
    main2()
