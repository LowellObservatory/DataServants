# -*- coding: utf-8 -*-
"""
  This Source Code Form is subject to the terms of the Mozilla Public
  License, v. 2.0. If a copy of the MPL was not distributed with this
  file, You can obtain one at http://mozilla.org/MPL/2.0/.

  Created on Fri Feb 23 14:36:02 2018

  @author: rhamilton
"""

from __future__ import division, print_function, absolute_import

import time
import sched
import signal
import datetime as dt

from pid import PidFile, PidFileError


def func1(arg1=None, arg2='world'):
    print("Func 1!")
    diff = dt.datetime.utcnow() - arg1
    print(diff.total_seconds())


def func2(arg1='hello', arg2='world'):
    print("Func 2!")
    diff = dt.datetime.utcnow() - arg1
    print(diff.total_seconds())


def func3(arg1='hello', arg2='world'):
    print("Func 3!")
    diff = dt.datetime.utcnow() - arg1
    print(diff.total_seconds())


class TimeOutException(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


def gotAlarm(signum, frame):
    print("Took too long! Raising TimeOutException.")
    raise TimeOutException


def scheduleMaster(s):
    print("Making the schedule")

    ival1 = 10.
    ival2 = 15.
    ival3 = 30.
    st = dt.datetime.utcnow()

    ev1 = s.enter(ival1, priority=1, action=func1,
                  kwargs={'arg1': st, 'arg2': 'one'})
    ev2 = s.enter(ival2, priority=1, action=func2,
                  kwargs={'arg1': st, 'arg2': 'two'})
    ev3 = s.enter(ival3, priority=2, action=func3,
                  kwargs={'arg1': st, 'arg2': 'three'})

    print(ev1)
    print(ev2)
    print(ev3)
    print("Scheduler start")
    s.run()
    print("Scheduler done")


if __name__ == "__main__":
    try:
        with PidFile(pidname='test', piddir='/tmp') as p:
            print(p.pid)
            print(p.filename)
            print(p.piddir)
            # Set schedule handler
            s = sched.scheduler(time.time, time.sleep)

            # Set signal handler
            signal.signal(signal.SIGALRM, gotAlarm)

            # Actually arm the alarm
            alarmtime = 30
            signal.alarm(alarmtime)
            print("Set an alarm for %d seconds" % (alarmtime))

            try:
                scheduleMaster(s)
            except TimeOutException:
                print("Giving up.")
            # Disable the alarm
            signal.alarm(0)
    except PidFileError as err:
        print(str(err))
