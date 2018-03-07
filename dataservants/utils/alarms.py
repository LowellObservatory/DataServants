# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on Thu Feb 22 14:40:01 2018
#
#  @author: rhamilton

"""Utilities to set, clear, and handle timing alarms set via :mod:`signal`.

.. warning::
    Some of these are in flux; it's clear that the class-based way is
    good in some ways but there's a duplication of code here that
    needs to be taken care of since they have diverged slightly.
"""

from __future__ import division, print_function, absolute_import

import signal


class TimeoutException(Exception):
    """Exception thrown when signal.alarm goes off.

    This class really does nothing except throw a generic exception class.
    It isn't subclassed any further and the arbitrary arguments are
    passed through verbatim.

    Args:
        *args: Variable length argument list.
        **kwargs: Arbitrary keyword arguments.
    """
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


def setAlarm(handler=None, timeout=10, debug=False):
    """Set an alarm via :mod:`signal.alarm` for timeout seconds.

    Analogous to :func:`dataservants.utils.alarms.setAlarm`,
    but with a hardcoded handler function
    :func:`raiseTimeout` called when
    the timeout is exceeded.

    Args:
        handler (function, optional)
            Pointer or reference to function to be called when the alarm
            runs out and TimeoutException is thrown.  Defaults to None.
            If None, then the handler :func:`raiseTimeout` is used.
        timeout (:obj:`int`, optional)
            Integer number of seconds to wait after which TimeoutException
            is thrown and the handler is used.
        debug (:obj:`bool`, optional)
            Bool to trigger additional debugging outputs. Defaults to False.

    .. note::
        Timeout can be integer only!
    """
    if timeout < 1:
        if debug is True:
            print("Warning: Timeout must be an integer >= 1")
        timeout = 1
    if type(timeout) is float:
        if debug is True:
            print("Warning: Timeout %f set to %d" % (timeout,
                                                     int(timeout)))
        timeout = int(timeout)

    if handler is not None:
        signal.signal(signal.SIGALRM, handler)
    else:
        signal.signal(signal.SIGALRM, raiseTimeout)
    signal.alarm(timeout)


def clearAlarm():
    """Clear any active signal alarms.

    Same as the class method, calls ``signal.alarm(0)``
    which nullifies an active alarm.
    """
    signal.alarm(0)


def raiseTimeout(signum, frame):
    """Raise the :class:`TimeoutException` when the alarm goes off.

    Args:
        signum (:obj:`int`)
            A signal number indicating which signal was recieved.
            See :obj:`signal` for details or in a terminal look
            at the output of ``kill -l``.
        frame (:obj:`frame`)
            Stack frame of where the interrupt occured.

    Raises:
        :class:`TimeoutException`
    """
    raise TimeoutException


class alarming(object):
    """A class to contain an alarm instance.

    This class creates and maintans an alarm instance
    object which can be both passed around and
    used to change the timeout exception handler function.

    .. warning::
        It references and calls functions defined already, so it's really
        just a convienence class that could probably be done away with.
    """
    def raiseTimeout(self, signum, frame):
        """Raise the :class:`TimeoutException` when the alarm goes off.

        .. seealso:: :func:`raiseTimeout`
        """
        raise TimeoutException

    def setAlarm(self, handler=None, timeout=10, debug=False):
        """Set an alarm via :func:`signal.alarm` for timeout seconds.

        .. seealso:: :func:`setAlarm`
        """
        setAlarm(handler=handler, timeout=timeout, debug=debug)

    def clearAlarm(self):
        """Clear any active signal alarms.

        .. seealso:: :func:`clearAlarm`
        """
        clearAlarm()
