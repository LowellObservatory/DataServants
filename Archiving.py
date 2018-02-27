# -*- coding: utf-8 -*-
"""
  This Source Code Form is subject to the terms of the Mozilla Public
  License, v. 2.0. If a copy of the MPL was not distributed with this
  file, You can obtain one at http://mozilla.org/MPL/2.0/.

  Created on Thu Feb 15 11:10:10 2018

  @author: rhamilton
"""

from __future__ import division, print_function, absolute_import

import sys
import time
import json

from wadsworth.utils import ssh
from wadsworth.utils import confparsers
from wadsworth.butler import buttle


def checkFreeSpace(sshConn, basecmd, sdir):
    """
    """
    fcmd = "%s -f %s" % (basecmd,  sdir)
    res = sshConn.sendCommand(fcmd)

    return res


def lookForNewDirectories(sshConn, basecmd, sdir, dirmask, age=2, debug=False):
    """
    """
    fcmd = "%s -l %s -r %s --rangeNew %d" % (basecmd,  sdir, dirmask, age)
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


if __name__ == "__main__":
    #
    # NOTE: Any command line arguments are passed directly to
    #   wadsworth the butler (wadsworth/butler/parseargs.py)
    #
    # idict: dictionary of parsed config file
    # args: parsed options of wadsworth.py
    # runner: class that contains logic to quit nicely
    # pid: PID of wadsworth.py
    # pidf: location of PID file containing PID of wadsworth.py
    idict, args, runner, pid, pidf = buttle.beginButtling(logfile=False)
    idict = confparsers.parsePassConf('./passwords.conf', idict)

    # InfluxDB database name to store stuff in
    dbname = 'LIGInstruments'

    print(args)

    # Preamble/contextual messages before we really start
    print("Beginning to archive the following instruments:")
    print("%s\n" % (' '.join(idict.keys())))
    print("Starting the infinite archiving loop.")
    print("Kill PID %d to stop it." % (pid))

    # Note: We need to prepend the PATH setting here because some hosts
    #   (all recent OSes, really) have a more stringent SSHd config
    #   that disallows the setting of random environment variables
    #   at login, and I can't figure out the goddamn pty shell settings
    #   for Ubuntu (Vishnu) and OS X (xcam)
    #
    # Also need to make sure to use the relative path (~/) since OS X
    #   puts stuff in /Users/<username> rather than /home/<username>
    baseYcmd = 'export PATH="~/miniconda3/bin:$PATH";'
    baseYcmd += 'python ~/DataMaid/yvette.py'
    baseYcmd += ' '

    # temp hack
    args.rangeNew = 2

    # Infinite archiving loop
    while runner.halt is False:
        for inst in idict:
            iobj = idict[inst]
            print("\n%s" % ("="*11))
            print("Instrument: %s" % (inst))

            # Open the SSH connection; SSHHandler creates a Persistence class
            #   (in sshConnection.py) which has some retries and timeout
            #   logic baked into it so we don't have to deal with it here
            eSSH = ssh.SSHHandler(host=iobj.host,
                                  port=iobj.port,
                                  username=iobj.user,
                                  timeout=iobj.timeout,
                                  password=iobj.password)
            eSSH.openConnection()
            time.sleep(1)
            fs = checkFreeSpace(eSSH, baseYcmd, iobj.srcdir)
            fsa = decodeAnswer(fs, debug=args.debug)
            print(fsa)

            time.sleep(3)
            nd = lookForNewDirectories(eSSH, baseYcmd,
                                       iobj.srcdir, iobj.dirmask,
                                       age=args.rangeNew)
            nda = decodeAnswer(nd, debug=args.debug)
            print(nda)
            time.sleep(3)
            eSSH.closeConnection()

            # Check to see if someone asked us to quit before continuing
            if runner.halt is True:
                break
            time.sleep(10)

        # Temporary hack to only run through once
        break

    # The above loop is exited when someone sends wadsworth.py SIGTERM...
    #   (via 'kill' or 'wadsworth.py -k') so once we get that, we'll clean
    #   up on our way out the door with one final notification to the log
    print("PID %d is now out of here!" % (pid))

    # The PID file will have already been either deleted or overwritten by
    #   another function/process by this point, so just give back the console
    #   and return STDOUT and STDERR to their system defaults
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__
    print("Archive loop completed; STDOUT and STDERR reset.")
