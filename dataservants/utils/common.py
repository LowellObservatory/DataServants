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
            print("Got signal num. %s; stopping..." % (signum))
        try:
            pids.remove_pid_file()
        except OSError as e:
            # Need to define why the file can't be removed here...
            print(str(e))

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
        #   Could get all fancy-pants with assignment, but we're not to make
        #   sure that it's always clear what should be in the conf file

        # Assign them first just to make sure they always exist
        self.name = ''
        self.host = ''
        self.port = 22
        self.user = ''
        self.srcdir = ''
        self.destdir = ''
        self.enabled = False
        self.engEnabled = False
        self.running = False
        self.timeout = 60
        if conf is not None:
            try:
                self.name = conf['name']
                print("\tname = %s" % (self.name))
                self.host = conf['host']
                print("\thost = %s" % (self.host))
                self.port = conf['port']
                print("\tport = %s" % (self.port))
                self.user = conf['user']
                print("\tuser = %s" % (self.user))
                self.srcdir = conf['srcdir']
                print("\tsrcdir = %s " % (self.srcdir))
                self.dirmask = conf['dirmask']
                print("\tdirmask = %s " % (self.dirmask))
                self.destdir = conf['destdir']
                print("\tdestdir = %s" % (self.destdir))

                # If you think about these last two, I promise it'll make sense
                #   It's a cheap way to actually get the right bool back, since
                #   typecasting won't work; bool('False') == True
                self.enabled = 'true' == conf['enabled'].lower()
                print("\tenabled = %s" % (str(self.enabled)))
                self.engEnabled = 'true' == conf['engEnabled'].lower()
                print("\tengEnabled = %s" % (str(self.engEnabled)))

                print()
            except KeyError as err:
                if parseHardFail is True:
                    nicerExit(err)
                else:
                    key = err.args[0]
                    setattr(self, key, None)
                    print("\t%s = None" % (key))

    def addPass(self, password=None, debug=False):
        """
        """
        if password is None:
            if debug is True:
                print("Password is empty!!")
        else:
            self.password = password
