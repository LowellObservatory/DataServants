"""alarm.py: Permits multiple SIGALRM events to be queued.

Uses a `heapq` to store the objects to be called when an alarm signal is
raised, so that the next alarm is always at the top of the heap.

I didn't write this, but I found it on StackOverflow and then cleaned up
the formatting to satisfy my PyLint settings.

From StackOverflow
https://stackoverflow.com/a/34999808

which is a lightly modified version of MIT licensed ActiveState/Code
https://github.com/ActiveState/code/tree/master/recipes/Python/577600_Queue_managing_multiple_SIGALRM_alarms
"""

from __future__ import division, print_function, absolute_import

import heapq
import signal
import datetime as dt
from time import time, sleep

from pid import PidFile, PidFileError

__version__ = '$Revision: 2539 $'.split()[1]

alarmlist = []


def __new_alarm(t, f, a, k):
    return (t + time(), f, a, k)


def __next_alarm():
    return int(round(alarmlist[0][0] - time())) if alarmlist else None


def __set_alarm():
    return signal.alarm(max(__next_alarm(), 1))


class TimeoutError(Exception):
    def __init__(self, message, id_=None):
        self.message = message
        self.id_ = id_


class Timeout:
    ''' id_ allows for nested timeouts. '''
    def __init__(self, id_=None, seconds=1, error_message='Timeout'):
        self.seconds = seconds
        self.error_message = error_message
        self.id_ = id_

    def handle_timeout(self):
        raise TimeoutError(self.error_message, self.id_)

    def __enter__(self):
        self.this_alarm = alarm(self.seconds, self.handle_timeout)

    def __exit__(self, type, value, traceback):
        try:
            cancel(self.this_alarm)
        except ValueError:
            pass


def __clear_alarm():
    """Clear an existing alarm.

    If the alarm signal was set to a callable other than our own, queue the
    previous alarm settings.
    """
    oldsec = signal.alarm(0)
    oldfunc = signal.signal(signal.SIGALRM, __alarm_handler)
    if oldsec > 0 and oldfunc != __alarm_handler:
        heapq.heappush(alarmlist, (__new_alarm(oldsec, oldfunc, [], {})))


def __alarm_handler(*zargs):
    """Handle an alarm by calling any due heap entries and resetting the alarm.

    Note that multiple heap entries might get called, especially if calling an
    entry takes a lot of time.
    """
    try:
        nextt = __next_alarm()
        while nextt is not None and nextt <= 0:
            (tm, func, args, keys) = heapq.heappop(alarmlist)
            func(*args, **keys)
            nextt = __next_alarm()
    finally:
        if alarmlist:
            __set_alarm()


def alarm(sec, func, *args, **keys):
    """Set an alarm.

    When the alarm is raised in `sec` seconds, the handler will call `func`,
    passing `args` and `keys`. Return the heap entry (which is just a big
    tuple), so that it can be cancelled by calling `cancel()`.
    """
    __clear_alarm()
    try:
        newalarm = __new_alarm(sec, func, args, keys)
        heapq.heappush(alarmlist, newalarm)
        return newalarm
    finally:
        __set_alarm()


def cancel(alarm):
    """Cancel an alarm by passing the heap entry returned by `alarm()`.

    It is an error to try to cancel an alarm which has already occurred.
    """
    __clear_alarm()
    try:
        alarmlist.remove(alarm)
        heapq.heapify(alarmlist)
    finally:
        if alarmlist:
            __set_alarm()


class processDescription():
    def __init__(self, **kwargs):
        self.func = None
        self.timedelay = 0.
        self.priority = 5
        self.args = []
        self.kwargs = {}

        for each in kwargs:
            setattr(self, each, kwargs[each])


def instActions(acts=[processDescription()], debug=True):
    """
    """
    answers = []
    for i, each in enumerate(acts):
        if debug is True:
            print("Function #%d, %s" % (i, each.func))
        # * and ** will unpack each of them properly
        answers.append(each.func(*each.args, **each.kwargs))
        sleep(each.timedelay)
        print("%s success! Moving on." % (each.func))

    return answers


def func1(arg1, arg2='world'):
    fs = dt.datetime.utcnow()
    print("Func %s!" % (arg2))
    diff = dt.datetime.utcnow() - arg1
    print("Started %f since loop start" % (diff.total_seconds()))
    # This sleep should be long enough that it causes a conflict in timing
    #   between func and insttimer and raise an exception
    sleep(25)
    print("Slept for %f" % ((dt.datetime.utcnow() - fs).total_seconds()))

    return 'Beeeeeeeees'


def func2(arg1, arg2='world'):
    fs = dt.datetime.utcnow()
    print("Func %s!" % (arg2))
    diff = dt.datetime.utcnow() - arg1
    print("Started %f since loop start" % (diff.total_seconds()))
    sleep(15)
    print("Slept for %f" % ((dt.datetime.utcnow() - fs).total_seconds()))

    return 'Penguins'


def func3(arg1, arg2='world'):
    fs = dt.datetime.utcnow()
    print("Func %s!" % (arg2))
    diff = dt.datetime.utcnow() - arg1
    print("Started %f since loop start" % (diff.total_seconds()))
    sleep(10)
    print("Slept for %f" % ((dt.datetime.utcnow() - fs).total_seconds()))

    return 'Harry Potter'


if __name__ == "__main__":
    # Loop time to count to before blowing up and moving on
    acttimer = 20.
    insttimer = 30.

    # Define our desired actions within the main loop
    v = dt.datetime.utcnow()
    act1 = processDescription(func=func1, name="Func1", timedelay=5.,
                              args=[v], kwargs={'arg2': 'one'})
    act2 = processDescription(func=func2, name="Func2", timedelay=5.,
                              args=[v], kwargs={'arg2': 'two'})
    act3 = processDescription(func=func3, name="Func3", timedelay=5.,
                              args=[v], kwargs={'arg2': 'thr'})

    acts = [act1, act2, act3]
    try:
        with PidFile(pidname='test', piddir='/tmp') as p:
            # Print PIDFile info
            print(p.pid, p.filename)

            # Setup timer stuff for entire loop
            try:
                with Timeout(id_='InstLoop', seconds=insttimer):
                    # Pre-fill our expected answers so we can see who fails
                    allanswers = [None]*len(acts)
                    for i, each in enumerate(acts):
                        try:
                            ans = None
                            # Remember to pass the individual actiontimer!
                            with Timeout(id_=each.name, seconds=acttimer):
                                astart = dt.datetime.utcnow()
                                ans = each.func(*each.args, **each.kwargs)
                                print(ans)
                        except TimeoutError as e:
                            print("Raised TimeOut for " + e.id_)
                            # Need a little extra care here since TimeOutError
                            #   could be from InstLoop *or* each.func, so
                            #   if we got the InstLoop exception, break out
                            if e.id_ == "InstLoop":
                                break
                            print(ans)
                        finally:
                            rnow = dt.datetime.utcnow()
                            print("Done with action, %f since start" %
                                  ((rnow - astart).total_seconds()))
                            allanswers[i] = ans
                    sleep(each.timedelay)
            except TimeoutError as e:
                print("Raised TimeOut for " + e.id_)


            print("Done with instrument")
    except PidFileError as err:
        print("Process already running! Close the other one.")
        print(str(err))

    print(allanswers)
