# -*- coding: utf-8 -*-
"""
Created on Mon Feb 26 11:37:03 2018

@author: rhamilton
"""

from __future__ import division, print_function, absolute_import

import sys
import signal
import argparse as argp
from collections import OrderedDict

from . import pids

try:
    import configparser as conf
except ImportError:
    import ConfigParser as conf


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
    def __init__(self, conf=None):
        # This should mirror what's in the configuration file
        #   Could get all fancy-pants with assignment, but we're not to make
        #   sure that it's always clear what should be in the conf file

        # Assign them first just to make sure they always exist
        self.name = ''
        self.host = ''
        self.port = 22
        self.user = ''
        self.srcdir = ''
        self.enabled = False
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

                # If you think about these last two, I promise it'll make sense
                #   It's a cheap way to actually get the right bool back, since
                #   typecasting won't work; bool('False') == True
                self.enabled = 'true' == conf['enabled'].lower()
                print("\tenabled = %s" % (str(self.enabled)))
                print()
            except KeyError as err:
                print("Key not found: %s" % (str(err)))
                nicerExit(err)

    def addPass(self, password=None, debug=False):
        """
        """
        if password is None:
            if debug is True:
                print("Password is empty!!")
        else:
            self.password = password


def parseInstConf(filename, debug=False):
    """
    Parse the .conf file that gives the setup per instrument
    Returns an ordered dict of Instrument classes that the conf file
    has 'enabled=True'
    """
    try:
        config = conf.SafeConfigParser()
        config.read_file(open(filename, 'r'))
    except IOError as err:
        nicerExit(err)

    print("Found the following instruments in the configuration file:")
    sections = config.sections()
    tsections = ' '.join(sections)
    print("%s\n" % tsections)

    print("Attempting to assign the configuration parameters...")
    inlist = []
    for each in sections:
        print("Applying '%s' section of conf. file..." % (each))
        inlist.append(InstrumentHost(conf=config[each]))

    # Making a dict of *just* the active instruments
    idict = OrderedDict()
    for inst in inlist:
        if inst.enabled is True:
            idict.update({inst.name: inst})

    return idict


def parsePassConf(filename, idict, debug=False):
    """
    Parse the .conf file that gives the passwords per user.

    Returns an ordered dict of results, that then need to be associated with
    the idict returned from parseInstConf.
    """
    try:
        config = conf.SafeConfigParser()
        config.read_file(open(filename, 'r'))
    except IOError as err:
        nicerExit(err)

    print("Found the following usernames in the password file:")
    sections = config.sections()
    tsections = ' '.join(sections)
    print("%s\n" % tsections)

    for each in idict.keys():
        # Get the username for this instrument
        iuser = idict[each].user
        # Now see if we have a password for this username
        try:
            passw = config[iuser]['pw']
        except KeyError:
            if debug is True:
                print("Username %s has no password!" % (iuser))
            passw = None

        if debug is True:
            print(iuser, passw)
        idict[each].addPass(passw)

    return idict


def parseArguments():
    """
    Setup command line arguments that could be used if so desired.
    """

    fclass = argp.ArgumentDefaultsHelpFormatter

    parser = argp.ArgumentParser(description='Alfred: The Instrument Monitor',
                                 formatter_class=fclass)

    parser.add_argument('-c', '--config', metavar='/path/to/file.log',
                        type=str,
                        help='File for instrument configuration information',
                        default='./instruments.conf', nargs='?')

    parser.add_argument('-l', '--log', metavar='/path/to/file.log', type=str,
                        help='File for logging of information/status messages',
                        default='/tmp/wadsworth.log', nargs='?')

    parser.add_argument('-k', '--kill', action='store_true',
                        help='Kill an already running instance of Wadsworth',
                        default=False)

    # Note: Need to specify dest= here since there are multiple long options
    #   (and I prefer the fun option name in the code)
    lhtext = 'Kill another Alfred instance, then take its place'
    parser.add_argument('-r', '--restart', '--fratricide', action='store_true',
                        help=lhtext, dest='fratricide',
                        default=False)

    parser.add_argument('-n', '--nlogs', type=int,
                        help='Number of previous logs to keep after rotation',
                        default=30, nargs=1)

    parser.add_argument('--debug', action='store_true',
                        help='Print extra debugging messages while running',
                        default=False)

    args = parser.parse_args()

    return args
