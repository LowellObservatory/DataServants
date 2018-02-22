# -*- coding: utf-8 -*-
"""
Created on Thu Feb 22 14:40:01 2018

@author: rhamilton
"""

from __future__ import division, print_function, absolute_import

import signal


def setAlarm(timeout=10, debug=False):
    """
    Given some arbitrary function, set an alarm to go off after timeout secs.
    and issue a TimeoutException if the alarm goes off.

    Timeout can be integer only!
    """
    if timeout < 1:
        if debug is True:
            print("Warning: Timeout must be an integer >= 1")
        timeout = 1
    if type(timeout) is float:
        if debug is True:
            print("Warning: Timeout %f set to %d" % (timeout, int(timeout)))
        timeout = int(timeout)

    signal.signal(signal.SIGALRM, raiseTimeout)
    signal.alarm(timeout)


def clearAlarm():
    signal.alarm(0)


def raiseTimeout(signum, frame):
    """
    """
    raise TimeoutException


class TimeoutException(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)