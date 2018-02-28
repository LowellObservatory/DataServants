# -*- coding: utf-8 -*-
"""
  This Source Code Form is subject to the terms of the Mozilla Public
  License, v. 2.0. If a copy of the MPL was not distributed with this
  file, You can obtain one at http://mozilla.org/MPL/2.0/.

  Created on Thu Feb 15 11:10:10 2018

  @author: rhamilton
"""

from __future__ import division, print_function, absolute_import

import os
import time
import signal

from .. import utils
from . import parseargs


def beginValeting(procname='Alfred', pidfile='alfred.pid', logfile=True):
    """
    """
    # Time to wait after a process is murdered before starting up again.
    #   Might be over-precautionary, but it gives time for the previous process
    #   to write whatever to the log and then close the file nicely.
    killSleep = 30

    # Debugging
    print("Current PID: %d" % (os.getpid()))

    # Setup termination signals
    runner = utils.common.HowtoStopNicely()
    runner.pidfile = pidfile

    # Setup argument parsing *before* logging so help messages go to stdout
    #   NOTE: This function sets up the default values when given no args!
    args = parseargs.parseArguments()

    pid = utils.pids.check_if_running(procname=procname,
                                      filename=runner.pidfile)
    # UGLY LOGIC I'M NOT HAPPY WITH
    if pid != -1:
        if (args.fratricide is True) or (args.kill is True):
            print("Sending SIGTERM to %d" % (pid))
            try:
                os.kill(pid, signal.SIGTERM)
            except Exception as err:
                print("Process not killed; why?")
                # Returning STDOUT and STDERR to the console/whatever
                utils.common.nicerExit(err)

            # If the SIGTERM took, then continue onwards. If we're killing,
            #   then we quit immediately. If we're replacing, then continue.
            if args.kill is True:
                print("Sent SIGTERM to PID %d" % (pid))
                # Returning STDOUT and STDERR to the console/whatever
                utils.common.nicerExit()
            else:
                print("LOOK AT ME I'M THE VALET NOW")
                print("%d second pause to allow the other process to exit." %
                      (killSleep))
                time.sleep(killSleep)
        else:
            # If we're not killing or replacing, just exit.
            #   But return STDOUT and STDERR to be safe
            utils.common.nicerExit()
    else:
        if args.kill is True:
            print("No %s process to kill!" % (procname))
            print("Seach for it manually:")
            print("ps -ef | grep -i '%s'" % (procname))
            utils.common.nicerExit()

    # Record the active PID in the (default) file
    pid, pidf = utils.pids.write_pid_file(filename=runner.pidfile)
    runner.pidfile = pidf

    if logfile is True:
        # Setup logging (optional arguments shown for clarity)
        utils.logs.setup_logging(logName=args.log, nLogs=args.nlogs)

    # Helps to put context on when things are stopped/started/restarted
    print("PID %d recorded at %s now starting..." % (pid, pidf))

    # Read in the configuration file and act upon it
    idict = utils.confparsers.parseInstConf(args.config, debug=True,
                                            parseHardFail=False)

    # If there's a password file, associate that with the above
    idict = utils.confparsers.parsePassConf(args.passes, idict,
                                            debug=args.debug)

    return idict, args, runner, pid, pidf
