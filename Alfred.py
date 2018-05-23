# -*- coding: utf-8 -*-
#
#   This Source Code Form is subject to the terms of the Mozilla Public
#   License, v. 2.0. If a copy of the MPL was not distributed with this
#   file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#   Created on Thu Feb 15 11:10:10 2018
#
#   @author: rhamilton

from __future__ import division, print_function, absolute_import

import os
import sys
import time
import signal
import datetime as dt

from ligmos import utils
from dataservants import alfred
from dataservants import yvette

from pid import PidFile, PidFileError


def defineActions():
    """
    """
    # Renaming import to keep line length sensible
    yvetteR = yvette.remote
    alfredT = alfred.tasks

    # Set up the desired actions using a helpful class to pass things
    #   to each function/process more clearly.
    #
    #   Note that we need to also update things per-instrument when
    #   inside the main loop via updateArguments()...it's just helpful to
    #   do the definitions out here for the constants and for clarity.
    act1 = utils.common.processDescription(func=alfredT.actionPing,
                                           name='CheckPing',
                                           timedelay=3.,
                                           maxtime=120,
                                           needSSH=False,
                                           args=[],
                                           kwargs={})

    act2 = utils.common.processDescription(func=yvetteR.actionSpace,
                                           name='CheckFreeSpace',
                                           timedelay=3.,
                                           maxtime=120,
                                           needSSH=True,
                                           args=[],
                                           kwargs={})

    act3 = utils.common.processDescription(func=yvetteR.actionStats,
                                           name='CheckStats',
                                           timedelay=3.,
                                           maxtime=120,
                                           needSSH=True,
                                           args=[],
                                           kwargs={})

    act4 = utils.common.processDescription(func=yvetteR.actionProcess,
                                           name='CheckProcess',
                                           timedelay=3.,
                                           maxtime=120,
                                           needSSH=True,
                                           args=[],
                                           kwargs={})

    actions = [act1, act2, act3, act4]

    return actions


def updateArguments(actions, iobj, args, dbname=None):
    """
    """
    # Update the functions with proper arguments.
    #   (opened SSH connection is added just before calling)
    # act1 == pings
    actions[0].args = [iobj]
    actions[0].kwargs = {'dbname': dbname,
                         'debug': args.debug}

    # act2 == check free space
    actions[1].args = [baseYcmd, iobj]
    actions[1].kwargs = {'dbname': dbname,
                         'debug': args.debug}

    # act3 == check target CPU/RAM stats
    actions[2].args = [baseYcmd, iobj]
    actions[2].kwargs = {'dbname': dbname,
                         'debug': args.debug}

    # act4 == Check on process health
    actions[3].args = [baseYcmd, iobj]
    actions[3].kwargs = {'procName': iobj.procmon,
                         'dbname': dbname,
                         'debug': args.debug}

    return actions


if __name__ == "__main__":
    # For PIDfile stuff; kindly ignore
    mynameis = os.path.basename(__file__)
    if mynameis.endswith('.py'):
        mynameis = mynameis[:-3]
    pidpath = '/tmp/'

    # InfluxDB database name to store stuff in
    dbname = 'LIGInstruments'

    # Note: We need to prepend the PATH setting here because some hosts
    #   (all recent OSes, really) have a more stringent SSHd config
    #   that disallows the setting of random environment variables
    #   at login, and I can't figure out the goddamn pty shell settings
    #   for Ubuntu (Vishnu) and OS X (xcam)
    #
    # Also need to make sure to use the relative path (~/) since OS X
    #   puts stuff in /Users/<username> rather than /home/<username>
    #   Messy but necessary due to how I'm doing SSH
    baseYcmd = 'export PATH="~/miniconda3/bin:$PATH";'
    baseYcmd += 'python ~/LIG/DataServants/Yvette.py'
    baseYcmd += ' '

    # Interval between successive runs of the instrument polling (seconds)
    bigsleep = 600

    # Total time for entire set of actions per instrument
    alarmtime = 600

    # idict: dictionary of parsed config file
    # args: parsed options of wadsworth.py
    # runner: class that contains logic to quit nicely
    idict, args, runner = alfred.valet.beginValeting(procname=mynameis,
                                                     logfile=True)

    # Quick renaming to keep line length under control
    malarms = utils.multialarm

    # Actually define the function calls/references to functions
    actions = defineActions()

    try:
        with PidFile(pidname=mynameis.lower(), piddir=pidpath) as p:
            # Print the preamble of this particular instance
            #   (helpful to find starts/restarts when scanning thru logs)
            utils.common.printPreamble(p, idict)

            # Semi-infinite loop
            while runner.halt is False:
                # This is a common core function that handles the actions and
                #   looping over each instrument.  We keep the main while
                #   loop out here, though, so we can do stuff with the
                #   results of the actions from all the instruments.
                results = utils.common.instLooper(idict, runner, args,
                                                  actions, updateArguments,
                                                  dbname=dbname,
                                                  alarmtime=alarmtime)

                # After all the instruments are done, take a big nap
                if runner.halt is False:
                    print("Starting a big sleep")
                    # Sleep for bigsleep, but in small chunks to check abort
                    for i in range(bigsleep):
                        time.sleep(1)
                        if runner.halt is True:
                            break

            # The above loop is exited when someone sends SIGTERM
            print("PID %d is now out of here!" % (p.pid))

            # The PID file will have already been either deleted/overwritten by
            #   another function/process by this point, so just give back the
            #   console and return STDOUT and STDERR to their system defaults
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
            print("Archive loop completed; STDOUT and STDERR reset.")
    except PidFileError as err:
        # We've probably already started logging, so reset things
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        print("Already running! Quitting...")
        utils.common.nicerExit()
