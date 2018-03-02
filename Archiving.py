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
import sys
import time
import json
import signal
import datetime as dt

from pid import PidFile, PidFileError

from dataservants import utils
from dataservants import wadsworth


def actionScheduler(s, *args, **kwargs):
    """
    """
    st = dt.datetime.utcnow()
    print(st)


def spaceAction(eSSH, iobj, baseYcmd):
    """
    """
    fs = checkFreeSpace(eSSH, baseYcmd, iobj.srcdir)
    fsa = decodeAnswer(fs, debug=args.debug)
    # Now make the packet given the deserialized json answer
    meas = ['FreeSpace']
    tags = {'host': iobj.host}
    ts = dt.datetime.utcnow()
    if fsa != {}:
        fs = {'path': fsa['FreeSpace']['path'],
              'total': fsa['FreeSpace']['total'],
              'free': fsa['FreeSpace']['free'],
              'percentfree': fsa['FreeSpace']['percentfree']}
        # Make the packet
        packet = utils.packetizer.makeInfluxPacket(meas=meas,
                                                   ts=ts,
                                                   tags=tags,
                                                   fields=fs)
    else:
        packet = []
    if args.debug is True:
        print(packet)


def checkFreeSpace(sshConn, basecmd, sdir):
    """
    """
    fcmd = "%s -f %s" % (basecmd, sdir)
    res = sshConn.sendCommand(fcmd)

    return res


def lookForNewDirectories(sshConn, basecmd, sdir, dirmask, age=2, debug=False):
    """
    """
    fcmd = "%s -l %s -r %s --rangeNew %d" % (basecmd, sdir, dirmask, age)
    res = sshConn.sendCommand(fcmd, debug=debug)

    return res


def decodeAnswer(ans, debug=False):
    final = {}
    if ans[0] == 0:
        if ans[1] != '':
            final = json.loads(ans[1])
            if debug is True:
                print(final)
    return final


def instActions(acts=[utils.common.processDescription()], debug=True):
    """
    """
    for i, each in enumerate(acts):
        print("Function #%d, %s" % (i, each.func))

        res = each.func(*each.args, **each.kwargs)
        print(res)
        # event = s.enter(each.timedelay, priority=each.priority,
        #                 action=each.func,
        #                 argument=each.args, kwargs=each.kwargs)

    # nd = lookForNewDirectories(eSSH, baseYcmd,
    #                            iobj.srcdir, iobj.dirmask,
    #                            age=args.rangeNew)
    # nda = decodeAnswer(nd, debug=args.debug)
    # print(nda)

    # spaceAction(eSSH, iobj, baseYcmd)
    # time.sleep(3)


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
    baseYcmd += 'python ~/DataMaid/yvette.py'
    baseYcmd += ' '

    # Interval between successive runs of the instrument polling (seconds)
    bigsleep = 300

    # idict: dictionary of parsed config file
    # args: parsed options of wadsworth.py
    # runner: class that contains logic to quit nicely
    idict, args, runner = wadsworth.buttle.beginButtling(procname=mynameis,
                                                         logfile=False)

    # Set up the desired actions in the main loop, using a helpful class
    #   to pass things to each function/process more clearly
    #   Note that we can update things per-instrument when inside the loop
    #   it's just helpful to do the definitions out here for the constants

    act1 = utils.common.processDescription(func=lookForNewDirectories,
                                           timedelay=3.,
                                           priority=1,
                                           args=[],
                                           kwargs={})

    act2 = utils.common.processDescription(func=checkFreeSpace,
                                           timedelay=3.,
                                           priority=2,
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
                # Do the instrument stuff right up front
                for inst in idict:
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
                        actions[0].args = [eSSH, baseYcmd,
                                           iobj.srcdir, iobj.dirmask]
                        actions[0].kwargs = {'age': args.rangeNew,
                                             'debug': args.debug}

                        actions[1].args = [eSSH, baseYcmd, iobj.srcdir]

                        instActions(actions)

                        eSSH.closeConnection()

                        # Check to see if someone asked us to quit
                        if runner.halt is True:
                            print("Quit inner instrument loop")
                            break
                        else:
                            # Time to sleep between instruments
                            time.sleep(10)
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
