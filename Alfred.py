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

from dataservants import utils
from dataservants import alfred
from dataservants import yvette

from pid import PidFile, PidFileError


def instActions(acts=[utils.common.processDescription()], debug=True):
    """
    """
    for i, each in enumerate(acts):
        if debug is True:
            print("Function #%d, %s" % (i, each.func))
        # * and ** will unpack each of them properly
        res = each.func(*each.args, **each.kwargs)
        time.sleep(each.timedelay)
        print(res)


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
    baseYcmd += 'python ~/DataServants/Yvette.py'
    baseYcmd += ' '

    # Interval between successive runs of the instrument polling (seconds)
    bigsleep = 600

#    # idict: dictionary of parsed config file
#    # args: parsed options of wadsworth.py
#    # runner: class that contains logic to quit nicely
    idict, args, runner = alfred.valet.beginValeting(procname=mynameis)

    # Set up the desired actions in the main loop, using a helpful class
    #   to pass things to each function/process more clearly
    #   Note that we can update things per-instrument when inside the loop
    #   it's just helpful to do the definitions out here for the constants
    yvetteR = yvette.remote

    act1 = utils.common.processDescription(func=yvetteR.actionSpace,
                                           timedelay=3.,
                                           priority=2,
                                           args=[],
                                           kwargs={})

    act2 = utils.common.processDescription(func=yvetteR.actionPing,
                                           timedelay=3.,
                                           priority=1,
                                           args=[],
                                           kwargs={})

    actions = [act1, act2]

    try:
        with PidFile(pidname=mynameis.lower(), piddir=pidpath) as p:
            # Helps to put context on when things are stopped/started/restarted
            print("Current PID: %d" % (p.pid))
            print("PID %d recorded at %s now starting..." % (p.pid,
                                                             p.filename))

            # Preamble/contextual messages before we really start
            print("Beginning to monitor the following hosts:")
            print("%s\n" % (' '.join(idict.keys())))
            print("Starting the infinite loop.")
            print("Kill PID %d to stop it." % (p.pid))

            # Semi-infinite loop
            while runner.halt is False:
                for inst in idict:
                    iobj = idict[inst]
                    if args.debug is True:
                        print("\n%s" % ("=" * 11))
                        print("Instrument: %s" % (inst))
                    try:
                        # Arm an alarm that will stop this inner section
                        #   in case one instrument starts to hog the show
                        alarmtime = 600
                        signal.alarm(alarmtime)
                        iobj = idict[inst]

                        # Open the SSH connection; SSHHandler makes a class
                        #   (found in utils/ssh.py) which has some retries
                        #   and timeout logic baked into it so we don't have
                        #   to deal with it here
                        eSSH = utils.ssh.SSHHandler(host=iobj.host,
                                                    port=iobj.port,
                                                    username=iobj.user,
                                                    timeout=iobj.timeout,
                                                    password=iobj.password)
                        eSSH.openConnection()
                        time.sleep(3)

                        # Update the functions with proper arguments
                        actions[0].args = [eSSH, iobj, baseYcmd]
                        actions[0].kwargs = {'dbname': dbname,
                                             'debug': args.debug}

                        actions[1].args = [iobj]
                        actions[1].kwargs = {'dbname': dbname,
                                             'debug': args.debug}

                        instActions(actions)

                        eSSH.closeConnection()

                        # Check to see if someone asked us to quit
                        if runner.halt is True:
                            print("Quit inner instrument loop")
                            break
                        else:
                            # Time to sleep between instruments
                            time.sleep(5)
                    except utils.alarms.TimeoutException as err:
                        print("%s took too long! Moving on." % (inst))
                # After all the instruments are done, take a big nap
                if runner.halt is False:
                    # Sleep for bigsleep, but in small chunks to check abort
                    for i in range(bigsleep):
                        time.sleep(1)
                        if runner.halt is True:
                            break
            # The above loop is exited when someone sends wadsworth.py SIGTERM
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
