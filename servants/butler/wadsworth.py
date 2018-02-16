# -*- coding: utf-8 -*-
"""
  This Source Code Form is subject to the terms of the Mozilla Public
  License, v. 2.0. If a copy of the MPL was not distributed with this
  file, You can obtain one at http://mozilla.org/MPL/2.0/.

  Created on Fri Jan 19 12:57:25 2018

  @author: rhamilton
"""

from __future__ import division, print_function, absolute_import

import os
import sys
import time
import signal
import argparse as argp
from collections import OrderedDict

try:
    import configparser as conf
except ImportError:
    import ConfigParser as conf

from .. import utils


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
            utils.pids.remove_pid_file()
        except OSError as e:
            # Need to define why the file can't be removed here...
            print(str(e))

        self.halt = True


class Instrument():
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
                print("Key not found: %s" % (str(err)))
                nicerExit(err)


def parse_conffile(filename, debug=False):
    """
    Parse the .conf file that gives the setup per instrument

    Returns an ordered dict of Instrument classes that the conf file
    has 'enabled=True'
    """
    try:
        config = conf.SafeConfigParser()
        fp = open(filename)
        config.readfp(fp)
    except IOError as err:
        nicerExit(err)
    finally:
        fp.close()

    print("Found the following instruments in the configuration file:")
    sections = config.sections()
    tsections = ' '.join(sections)
    print("%s\n" % tsections)

    print("Attempting to assign the configuration parameters...")
    inlist = []
    for each in sections:
        print("Applying '%s' section of conf. file..." % (each))
        inlist.append(Instrument(conf=config[each]))

    # Making a dict of *just* the active instruments
    idict = OrderedDict()
    for inst in inlist:
        if inst.enabled is True:
            idict.update({inst.name: inst})

    return idict


def setup_arguments():
    """
    Setup command line arguments that could be used if so desired.
    """

    fclass = argp.ArgumentDefaultsHelpFormatter

    parser = argp.ArgumentParser(description='Wadsworth: The Data Butler',
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
    lhtext = 'Kill another Wadsworth instance, then take its place'
    parser.add_argument('-r', '--restart', '--fratricide', action='store_true',
                        help=lhtext, dest='fratricide',
                        default=False)

    parser.add_argument('-n', '--nlogs', type=int,
                        help='Number of previous logs to keep after rotation',
                        default=30, nargs=1)

    args = parser.parse_args()

    return args


def beginButtling():
    """
    """
    # Time to wait after a process is murdered before starting up again.
    #   Might be over-precautionary, but it gives time for the previous process
    #   to write whatever to the log and then close the file nicely.
    killSleep = 30

    # Debugging
    print("Current PID: %d" % (os.getpid()))

    # Setup termination signals
    runner = HowtoStopNicely()

    # Setup argument parsing *before* logging so help messages go to stdout
    #   NOTE: This function sets up the default values when given no args!
    args = setup_arguments()

    pid = utils.pids.check_if_running()
    # UGLY LOGIC I'M NOT HAPPY WITH
    if pid != -1:
        if (args.fratricide is True) or (args.kill is True):
            print("Sending SIGTERM to %d" % (pid))
            try:
                os.kill(pid, signal.SIGTERM)
            except Exception as err:
                print("Process not killed; why?")
                # Returning STDOUT and STDERR to the console/whatever
                nicerExit(err)

            # If the SIGTERM took, then continue onwards. If we're killing,
            #   then we quit immediately. If we're replacing, then continue.
            if args.kill is True:
                print("Sent SIGTERM to PID %d" % (pid))
                # Returning STDOUT and STDERR to the console/whatever
                nicerExit()
            else:
                print("LOOK AT ME I'M THE BUTLER NOW")
                print("%d second pause to allow the other process to exit." %
                      (killSleep))
                time.sleep(killSleep)
        else:
            # If we're not killing or replacing, just exit.
            #   But return STDOUT and STDERR to be safe
            nicerExit()
    else:
        if args.kill is True:
            print("No Wadsworth process to kill!")
            print("Seach for Wadsworth manually:")
            print("ps -ef | grep -i 'Wadsworth'")
            nicerExit()

    # Record the active PID in the (default) file
    pid, pidf = utils.pids.write_pid_file()

    # Setup logging (optional arguments shown for clarity)
    utils.logs.setup_logging(logName=args.log, nLogs=args.nlogs)

    # Helps to put context on when things are stopped/started/restarted
    print("PID %d recorded at %s now starting..." % (pid, pidf))

    # Read in the configuration file and act upon it
    idict = parse_conffile(args.config, debug=True)

    return idict, args, runner, pid, pidf
