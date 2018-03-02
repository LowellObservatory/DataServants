# -*- coding: utf-8 -*-
"""
  This Source Code Form is subject to the terms of the Mozilla Public
  License, v. 2.0. If a copy of the MPL was not distributed with this
  file, You can obtain one at http://mozilla.org/MPL/2.0/.

  Created on Thu Feb 15 16:58:53 2018

  @author: rhamilton
"""

from __future__ import division, print_function, absolute_import

import sys
import signal
import datetime as dt
from os.path import basename

from . import pids


def dateDiff(fstr, debug=False):
    """
    """
    dstr = basename(fstr)
    dtobj = strToDate(dstr)
    dtts = dt.datetime.timestamp(dtobj)
    now = dt.datetime.timestamp(dt.datetime.utcnow())
    diff = (now - dtts)

    if debug is True:
        print(dtobj, dtts, now, diff)

    return diff


def strToDate(st):
    """
    """
    # Try just the first 8 characters (20180214, 20180214a, 20180214_junk)
    dted = None
    try:
        dted = dt.datetime.strptime(st[0:8], "%Y%m%d")
    except ValueError:
        # Try some other ones
        if len(st) == 10:
            try:
                dted = dt.datetime.strptime(st, "%Y-%m-%d")
            except ValueError:
                pass

    return dted


def nicerExit(err=None):
    """
    """
    cond = 0
    if err is not None:
        print("FATAL ERROR: %s" % (str(err)))
        cond = -1

    # Returning STDOUT and STDERR to the console/whatever
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__

    sys.exit(cond)


class HowtoStopNicely():
    def __init__(self):
        """
        'kill PID' will issue SIGTERM, and this will handle it gracefully and
        delete the PID file so a clean start is possible.

        NOTE: 'kill -9' will issue SIGKILL and that can't be caught, but the
        logic in utils.check_if_running should let it start without a fuss.
        """
        # Set up signal handling before anything else!
        self.pidfile = None
        self.halt = False
        signal.signal(signal.SIGHUP, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def signal_handler(self, signum, frame):
        # Python3's signal module is way nicer...
        try:
            print("Got %s; stopping..." % (signal.Signals(signum).name))
        except AttributeError:
            # Shouldn't ever really get here, but I'll handle it anyways
            print("Got signal num. %s; stopping..." % (signum))

        self.halt = True


class InstrumentHost():
    """
    Defines all the things necessary to tell Wadsworth where to get
    and where to buttle data that is found.

    Takes an optional argument of a parsed configuration file; if the parsed
    structure exists and you pass it, the class will init with its contents
    """
    def __init__(self, conf=None, parseHardFail=True):
        # This should mirror what's in the configuration file
        # Assign them first just to make sure they always exist
        self.name = ''
        self.host = ''
        self.port = 22
        self.user = ''
        self.srcdir = ''
        self.destdir = ''
        self.dirmask = ''
        self.enabled = False
        self.engEnabled = False
        self.running = False
        self.timeout = 60
        if conf is not None:
            for key in self.__dict__:
                try:
                    if (key.lower() == 'enabled') or \
                       (key.lower() == 'engenabled'):
                        setattr(self, key, conf.getboolean(key))
                    elif (key.lower() == 'running') or \
                         (key.lower() == 'timeout'):
                        # Skip the keys that are self-defined in the class
                        pass
                    else:
                        setattr(self, key, conf[key])
                except KeyError as err:
                    if parseHardFail is True:
                        nicerExit(err)
                    else:
                        key = err.args[0]
                        setattr(self, key, None)
                print("\t%s = %s" % (key, getattr(self, key)))

    def addPass(self, password=None, debug=False):
        """
        """
        if password is None:
            if debug is True:
                print("Password is empty!!")
        else:
            self.password = password


class processDescription():
    def __init__(self, **kwargs):
        self.func = None
        self.timedelay = 0.
        self.priority = 5
        self.args = []
        self.kwargs = {}

        for each in kwargs:
            setattr(self, each, kwargs[each])
