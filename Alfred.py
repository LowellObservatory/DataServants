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

from pid import PidFile, PidFileError

from ligmos import utils
from ligmos import workers
from dataservants import alfred
from dataservants import yvette


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


def updateArguments(actions, iobj, args, baseYcmd, db=None):
    """
    """
    # Update the functions with proper arguments.
    #   (opened SSH connection is added just before calling)
    # act1 == pings
    actions[0].args = [iobj]
    actions[0].kwargs = {'db': db,
                         'debug': args.debug}

    # act2 == check free space
    actions[1].args = [baseYcmd, iobj]
    actions[1].kwargs = {'db': db,
                         'debug': args.debug}

    # act3 == check target CPU/RAM stats
    actions[2].args = [baseYcmd, iobj]
    actions[2].kwargs = {'db': db,
                         'debug': args.debug}

    # act4 == Check on process health
    actions[3].args = [baseYcmd, iobj]
    actions[3].kwargs = {'db': db,
                         'procName': iobj.procmon,
                         'debug': args.debug}

    return actions


def main():
    """
    """
    # For PIDfile stuff; kindly ignore
    mynameis = os.path.basename(__file__)
    if mynameis.endswith('.py'):
        mynameis = mynameis[:-3]
    pidpath = '/tmp/'

    # Define the default files we'll use/look for. These are passed to
    #   the worker constructor (toServeMan).
    conf = './alfred.conf'
    passes = './passwords.conf'
    logfile = '/tmp/alfred.log'
    desc = 'Alfred: The Instrument Monitor'
    eargs = alfred.parseargs.extraArguments

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

    # Quick renaming to keep line length under control
    ic = utils.common.hostTarget
    udb = utils.database

    # idict: dictionary of parsed config file
    # cblk: common block from config file
    # args: parsed options of wadsworth.py
    # runner: class that contains logic to quit nicely
    idict, cblk, args, runner = workers.workerSetup.toServeMan(mynameis, conf,
                                                               passes,
                                                               logfile,
                                                               desc=desc,
                                                               extraargs=eargs,
                                                               conftype=ic,
                                                               logfile=True)

    # abort = False will allow the code to continue if the file isn't found.
    #   That's because I've deemed extra pings "nice" but not "necessary"
    epings, _ = utils.confparsers.parseConfFile(args.extraPings,
                                                debug=args.debug,
                                                abort=False)

    # Actually define the function calls/references to functions
    actions = defineActions()

    try:
        with PidFile(pidname=mynameis.lower(), piddir=pidpath) as p:
            # Print the preamble of this particular instance
            #   (helpful to find starts/restarts when scanning thru logs)
            utils.common.printPreamble(p, idict)

            if cblk.dbtype.lower() == 'influxdb':
                # Create an influxdb object that can be spread around to
                #   connect and commit packets when they're created.
                #   Leave it disconnected initially.
                # TODO: Figure out how to fold in database passwords
                idb = udb.influxobj(cblk.dbname,
                                    host=cblk.dbhost,
                                    port=cblk.dbport,
                                    user=cblk.dbuser,
                                    pw=cblk.dbpass,
                                    connect=False)
            else:
                # No other database types are defined yet
                pass

            # Semi-infinite loop
            while runner.halt is False:
                # This is a common core function that handles the actions and
                #   looping over each instrument.  We keep the main while
                #   loop out here, though, so we can do stuff with the
                #   results of the actions from all the instruments.
                _ = utils.common.instLooper(idict, runner, args,
                                            actions, updateArguments,
                                            baseYcmd,
                                            db=idb,
                                            alarmtime=alarmtime)

                # Doing the extra pings as a side job/quickie
                #   No need to make this into a big to-do
                if epings is not None:
                    for sect in epings.sections():
                        # Check to see if this section is "enabled"
                        penab = epings[sect].getboolean('enabled')
                        if penab is True:
                            pobj = utils.common.baseTarget()
                            # Bit of a quick-and-dirty parse here, will fail
                            #   on typos/capitalization problems...
                            pobj.host = epings[sect]['host']
                            pobj.port = epings[sect]['port']

                            alfred.tasks.actionPing(pobj, db=idb,
                                                    debug=args.debug)
                        else:
                            print("Ping %s is disabled in conf file!" % (sect))

                # After all the instruments are done, take a big nap
                if runner.halt is False:
                    print("Starting a big sleep")
                    # Sleep for bigsleep, but in small chunks to check abort
                    for _ in range(bigsleep):
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
    except PidFileError:
        # We've probably already started logging, so reset things
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        print("Already running! Quitting...")
        utils.common.nicerExit()


if __name__ == "__main__":
    main()
