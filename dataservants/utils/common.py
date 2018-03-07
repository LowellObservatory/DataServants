# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on Thu Feb 15 16:58:53 2018
#
#  @author: rhamilton

from __future__ import division, print_function, absolute_import

import sys
import signal
import datetime as dt
from os.path import basename

from . import pids


class processDescription():
    """Class to collect function references and associated arguments.

    All attributes can be set during class instantiation and will be
    set to the specified values.  No checks are done for KeyErrors so it'll
    just make attributes all day.

    .. warning::
        ``**kwargs`` sent to processDescription as an argument
        are **different** than ``kwargs`` assigned to the attribute!
        The former allows setting all (and other) attributes of this class;
        the latter allows the sending of specific keyword arguments to
        ``func``!

    Args:
        **kwargs: Arbitrary keyword arguments.

    Attributes:
        func (:obj:`function`)
            Reference to the function that will be called with ``args``
            and ``kwargs`` specified in this class.
        timedelay (:obj:`int`)
            Time to sleep before calling ``func``.
        priority (:obj:`int`)
            Relative priority to assign to ``func`` if using :mod:`sched`.
        args (:obj:`list`)
            Positional arguments to send along to ``func``.
        kwargs (:obj:`dict`)
            Keyword arguments to send along to ``func``.

    .. image:: https://media.giphy.com/media/12NUbkX6p4xOO4/giphy.gif
    """
    def __init__(self, **kwargs):
        self.func = None
        self.timedelay = 0.
        self.priority = 5
        self.args = []
        self.kwargs = {}

        for each in kwargs:
            setattr(self, each, kwargs[each])


class HowtoStopNicely():
    """Class to catch signals and trigger the instantiating process to exit.

    Takes no arguments, but contains a few parameters to help pass
    the process information around.

    When ``SIGHUP``, ``SIGINT``, or ``SIGTERM`` is issued,
    :func:`signal_handler` will be called which will set ``halt`` to True.

    .. warning::
        It is the instantiating process' problem to periodically check if
        ``halt`` has been set to True and to act accordingly.

    Attributes:
        pidfile (:obj:`str`)
            String containing the path to the active PID sentinel file.
            Defaults to :obj:`None` and must be set after the class is inited.
        halt (:obj:`bool`)
            Bool representing whether the calling function should stop
            (== True) or continue onwards (== False).

    .. note::
        ``kill PID`` will issue ``SIGTERM``, and this will handle it
        gracefully so a clean start is possible.

        ``kill -9`` will issue ``SIGKILL`` and can never be caught.
        The logic in :func:`dataservants.utils.pids.check_if_running`
        should let the process start again, though.
    """
    def __init__(self):
        # Set up signal handling before anything else!
        self.pidfile = None
        self.halt = False
        signal.signal(signal.SIGHUP, self.signal_handler)
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

    def signal_handler(self, signum, frame):
        """Actions to take after a signal is caught.

        Sets the ``halt`` attribute to True, allowing the calling function
        to know that someone wants it to stop.

        Args:
            signum (:obj:`int`)
                A signal number indicating which signal was recieved.
                See :obj:`signal` for details or in a terminal look
                at the output of ``kill -l``.
            frame (:obj:`frame`)
                Stack frame of where the interrupt occured.
        """
        # Python3's signal module is way nicer...
        try:
            print("Got %s; stopping..." % (signal.Signals(signum).name))
        except AttributeError:
            # Shouldn't ever really get here, but I'll handle it anyways
            print("Got signal num. %s; stopping..." % (signum))

        self.halt = True


class InstrumentHost():
    """Contains the information to connect and find data on remote machines.

    This class is a workhorse, containing every piece of information needed
    to connect to remote machines, find data underneath some source directory
    matching a pattern, and the knowledge of where that data should go on the
    local host machine if archiving is being performed.

    All of these are set either manually or via a
    :class:`configparser.ConfigParser` configuration object
    returned by :func:`dataservants.utils.confparsers.parseInstConf` and
    :func:`dataservants.utils.confparsers.parsePassConf`.

    .. seealso::
        ``archiving.conf-TEMPLATE``, ``alfred.conf-TEMPLATE`` in the
        examples directory.

    Args:
        conf (:class:`configparser.ConfigParser`, optional)
            Configuration information parsed from a .conf file.
            Defaults to None.  If conf is not None, then the configuration
            is applied to the attributes via :func:`setattr` on self.  If the
            attribute doesn't exist in self, and ``parseHardFail`` is True,
            then :class:`KeyError` is raised.
        parseHardFail (:obj:`bool`)
            If True, and an attribute in ``conf`` does not exist in self,
            :class:`KeyError` is raised (not caught) causing an Exception.
            If False, the attribute is just skipped.

            .. note::
                This allows the use of a subset of options to be specified
                but the use of the same confparser, as is done for the .conf
                files for both :mod:`dataservants.alfred` and
                :mod:`dataservants.wadsworth`.

    Attributes:
        name (:obj:`str`)
            Nicer name to call specified host in output logs.
        host (:obj:`str`)
            Remote machine hostname to connect to. Could be an IP address too.
        port (:obj:`int`)
            Port in which to access ``host`` via SSH.
        user (:obj:`str`)
            Username to use when logging in to ``host``
        srcdir (:obj:`str`)
            Directory on remote host to look for data
        destdir (:obj:`str`)
            Directory on **local** host in which to place data being archived
        dirmask (:obj:`str`)
            Regular expression pattern to match against directories found
            that could contain data.

            .. seealso::
                :func:`dataservants.utils.files.getDirListing`
        enabled (:obj:`bool`)
            Boolean to control whether the given remote host is actually
            queried, or if it is disabled and not checked at all.
        engEnabled (:obj:`bool`)
            Boolean to control whether to look for and archive any
            additional engineering data.
        running (:obj:`bool`)
            Boolean to show whether archiving and checks of ``host`` are
            currently active
        timeout (:obj:`int`)
            Integer number of seconds that ``host`` can be actively archiving,
            checking, or doing things as timed on the **local** machine.

            .. note::
                This ensures that if a timeout of some sort occurs,
                one remote host won't block indefinitely.
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
        """Add in password information from a separate file for ``user``.

        This small function allows the breaking up of usernames from passwords
        into separate .conf files, mainly for a little extra security when
        posting this all to GitHub.

        .. seealso::
            ``passwords.conf-TEMPLATE`` in the examples directory.

        Args:
            password (conf (:class:`configparser.ConfigParser`, optional)
                Configuration information parsed from a .conf file.
                Defaults to None.  If password is not None, then a
                ``password`` attribute is created if matching usernames
                are found.
        debug (:obj:`bool`, optional)
            Bool to trigger additional debugging outputs. Defaults to False.
        """
        if password is None:
            if debug is True:
                print("Password is empty!!")
        else:
            self.password = password


def dateDiff(fstr, debug=False):
    """Attempt to determine how old a given string is from now.

    Depends entirely on :func:`strToDate` to convert the given
    string ``fstr`` into a datetime object.  Assumes that ``fstr`` is really
    a directory path, so it first takes the :func:`os.path.basename` of it.

    Args:
        fstr (:obj:`str`)
            Full path of a folder to be dated
        debug (:obj:`bool`, optional)
            Bool to trigger additional debugging outputs. Defaults to False.

    Returns:
        diff (:class:`datetime.timedelta`)
            Timedelta instance between now and the parsed
            and converted ``fstr``. If ``fstr`` couldn't be converted,
            diff will be :obj:`None`.
    """
    dstr = basename(fstr)
    dtobj = strToDate(dstr)
    if type(dtobj) is dt.datetime:
        dtts = dt.datetime.timestamp(dtobj)
        now = dt.datetime.timestamp(dt.datetime.utcnow())
        diff = (now - dtts)

        if debug is True:
            print(dstr, dtobj, dtts, now, diff)
    else:
        # Obvious bad value so others can deal with it in their logic
        diff = None

    return diff


def strToDate(st):
    """Attempt to convert the given string to a datetime.

    First assumes that just the first 8 characters are good enough,
    which would match strings like "20180415...".

    If that doesn't work, it tries to match strings like "2018-04-15".

    If that doesn't work, it gives up.  Could obviously be extended further.

    Args:
        st (:obj:`str`)
            String to attempt to convert

    Returns:
        dted (:class:`datetime.datetime`)
            Datetime instance converted from string, using
            :func:`datetime.strptime`.

            .. note::
                :func:`datetime.strptime` is hard to link to, so look at
                :func:`time.strptime`, and the stuff defined in
                :func:`time.strftime`.  See also the helpful table at
                `strftime() and strptime() Behavior
                <https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior>`_.

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
                # dted will still be None at this point,
                #   so now it becomes the calling function's problem
                pass

    return dted


def nicerExit(err=None):
    """Signal handling function to reset any logging and then exit.

    Assuming logging is set up, this handler will reset :obj:`sys.stdout` and
    :obj:`sys.stderr` back to their original values to allow output to the
    console rather then hidden away in a log.

    If ``err`` is specified then print that to the log, **then** reset
    :obj:`sys.stdout` and :mod:`obj.stderr`.

    Args:
        err (:obj:`Exception` or :obj:`str`)
            Could be either data type, depending on how it is called.
            Defaults to None, indicating a clean exit.  If it is not None,
            then :func:`sys.exit` will be called with ``-1`` and a traceback
            might ensue, depending on your settings.
    """
    cond = 0
    if err is not None:
        print("FATAL ERROR: %s" % (str(err)))
        cond = -1

    # Returning STDOUT and STDERR to the console/whatever
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__

    sys.exit(cond)
