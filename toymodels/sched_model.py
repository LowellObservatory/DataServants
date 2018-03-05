# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on Fri Feb 23 14:36:02 2018
#
#  @author: rhamilton

from __future__ import division, print_function, absolute_import

import time
import sched
import signal
import datetime as dt

from pid import PidFile, PidFileError


class processDescription():
    def __init__(self, **kwargs):
        self.func = None
        self.timedelay = 0.
        self.priority = 5
        self.args = []
        self.kwargs = {}

        for each in kwargs:
            setattr(self, each, kwargs[each])


class TimeOutException(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


def func1(arg1, arg2='world'):
    print("Func %s!" % (arg2))
    diff = dt.datetime.utcnow() - arg1
    print(diff.total_seconds())
    # This sleep should be long enough that it causes a conflict in timing
    #   between func3 and func2 to illustrate the sequencing with delays
    time.sleep(25)

    return 'Beeeeeeeees'


def func2(arg1, arg2='world'):
    print("Func %s!" % (arg2))
    diff = dt.datetime.utcnow() - arg1
    print(diff.total_seconds())
    time.sleep(15)

    return 'Penguins'


def func3(arg1, arg2='world'):
    print("Func %s!" % (arg2))
    diff = dt.datetime.utcnow() - arg1
    print(diff.total_seconds())

    return 'Harry Potter'


def gotAlarm(signum, frame):
    print("Took too long! Raising TimeOutException.")
    raise TimeOutException


def scheduleMaster(s, actlist=[processDescription()]):
    print("Making the schedule")

    rt = dt.datetime.utcnow()

    elist = []
    for i, each in enumerate(actlist):
        print("Function %d" % (i))
        # Temporary hack to give the relative time since this function started
        #   to help in debugging the actual timing/sequence of things
        each.args = [rt]
        # Note that priority only takes effect if two events are *scheduled*
        #   for the same time; if there's a delay in one function, it
        #   won't really matter which of the next tasks has a higher priority
        event = s.enter(each.timedelay, priority=each.priority,
                        action=each.func,
                        argument=each.args, kwargs=each.kwargs)
        print(event)
        elist.append(event)

    print("Scheduler start")
    # How do I get the return values?
    s.run()
    print("Scheduler done")


if __name__ == "__main__":
    # Define our desired actions within the main loop
    v1 = 1
    v2 = dt.datetime.utcnow()
    act1 = processDescription(func=func1, timedelay=10., priority=3,
                              args=[v1, v2], kwargs={'arg2': 'one'})
    act2 = processDescription(func=func2, timedelay=20., priority=2,
                              args=[v1, v2], kwargs={'arg2': 'two'})
    act3 = processDescription(func=func3, timedelay=30., priority=1,
                              args=[v1, v2], kwargs={'arg2': 'thr'})
    try:
        with PidFile(pidname='test', piddir='/tmp') as p:
            # Print PIDFile info
            print(p.pid, p.filename)

            # Setup signal handler
            signal.signal(signal.SIGALRM, gotAlarm)

            # Set schedule handler
            s = sched.scheduler(time.time, time.sleep)

            try:
                # Actually arm the alarm just before we start
                alarmtime = 3000
                signal.alarm(alarmtime)
                print("Set an alarm for %d seconds" % (alarmtime))
                # Act out all the actions, each within their
                scheduleMaster(s, [act1, act2, act3])
            except TimeOutException:
                print("Giving up.")

            # Disable the alarm since everything went ok
            signal.alarm(0)
    except PidFileError as err:
        print("Process already running! Close the other one.")
        print(str(err))
