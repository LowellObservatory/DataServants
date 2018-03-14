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

from dataservants import utils
from dataservants import alfred
from dataservants import yvette

from pid import PidFile, PidFileError


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

    # Total time for entire set of actions per instrument
    alarmtime = 600

#    # idict: dictionary of parsed config file
#    # args: parsed options of wadsworth.py
#    # runner: class that contains logic to quit nicely
    idict, args, runner = alfred.valet.beginValeting(procname=mynameis)

    # Quick renaming to keep line length under control
    yvetteR = yvette.remote
    malarms = utils.multialarm

    # Set up the desired actions in the main loop, using a helpful class
    #   to pass things to each function/process more clearly
    #   Note that we can update things per-instrument when inside the loop
    #   it's just helpful to do the definitions out here for the constants
    act1 = utils.common.processDescription(func=yvetteR.actionPing,
                                           timedelay=3.,
                                           maxtime=120,
                                           args=[],
                                           kwargs={})

    act2 = utils.common.processDescription(func=yvetteR.actionSpace,
                                           timedelay=3.,
                                           maxtime=120,
                                           args=[],
                                           kwargs={})

    act3 = utils.common.processDescription(func=yvetteR.actionStats,
                                           timedelay=3.,
                                           maxtime=120,
                                           args=[],
                                           kwargs={})
    actions = [act1, act2, act3]

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
                        with malarms.Timeout(id_='InstLoop',
                                             seconds=alarmtime):
                            iobj = idict[inst]

                            # Open the SSH connection; SSHHandler makes a class
                            #   (found in utils/ssh.py) which has some logic
                            #   baked into it
                            #   Timeout here is the time before giving up
                            #   to establish a working SSH connection
                            eSSH = utils.ssh.SSHWrapper(host=iobj.host,
                                                        port=iobj.port,
                                                        username=iobj.user,
                                                        timeout=60,
                                                        password=iobj.password,
                                                        connectOnInit=True)
                            time.sleep(3)

                            # Update the functions with proper arguments
                            # act1 == check ping times
                            #   Technically this one doesn't need SSH opened,
                            #   but I want to keep these together for clarity
                            actions[0].args = [iobj]
                            actions[0].kwargs = {'dbname': dbname,
                                                 'debug': args.debug}

                            # act2 == check free space
                            actions[1].args = [eSSH, iobj, baseYcmd]
                            actions[1].kwargs = {'dbname': dbname,
                                                 'debug': args.debug}

                            # act3 == check target CPU/RAM stats
                            actions[2].args = [eSSH, iobj, baseYcmd]
                            actions[2].kwargs = {'dbname': dbname,
                                                 'debug': args.debug}

                            # Pre-fill our expected answers so we can see fails
                            allanswers = [None]*len(actions)
                            for i, each in enumerate(actions):
                                try:
                                    ans = None
                                    # Remember to pass actiontimer!
                                    with malarms.Timeout(id_=each.name,
                                                         seconds=each.maxtime):
                                        astart = dt.datetime.utcnow()
                                        ans = each.func(*each.args,
                                                        **each.kwargs)
                                        print(ans)
                                except malarms.TimeoutError as e:
                                    print("Raised TimeOut for " + e.id_)
                                    # Need a little extra care here since
                                    #   TimeOutError could be from InstLoop
                                    #   *or* each.func, so if we got the
                                    #   InstLoop exception, break out
                                    if e.id_ == "InstLoop":
                                        break
                                    print(ans)
                                finally:
                                    rnow = dt.datetime.utcnow()
                                    print("Done with action, %f since start" %
                                          ((rnow - astart).total_seconds()))
                                    allanswers[i] = ans
                                time.sleep(each.timedelay)

                            eSSH.closeConnection()

                        # Check to see if someone asked us to quit
                        if runner.halt is True:
                            print("Quit inner instrument loop")
                            break
                        else:
                            # Time to sleep between instruments
                            time.sleep(5)
                    except malarms.TimeoutError as err:
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
