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
import datetime as dt

from dataservants import alfred


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
    # InfluxDB database name to store stuff in
    dbname = 'LIGInstruments'

#    # idict: dictionary of parsed config file
#    # args: parsed options of wadsworth.py
#    # runner: class that contains logic to quit nicely
#    # pid: PID of wadsworth.py
#    # pidf: location of PID file containing PID of wadsworth.py
    idict, args, runner, pid, pidf = alfred.valet.beginValeting(logfile=False)

    # Preamble/contextual messages before we really start
    print("Beginning to monitor the following hosts:")
    print("%s\n" % (' '.join(idict.keys())))
    print("Starting the infinite loop.")
    print("Kill PID %d to stop it." % (pid))

    # Note: We need to prepend the PATH setting here because some hosts
    #   (all recent OSes, really) have a more stringent SSHd config
    #   that disallows the setting of random environment variables
    #   at login, and I can't figure out the goddamn pty shell settings
    #   for Ubuntu (Vishnu) and OS X (xcam)
    #
    # Also need to make sure to use the relative path (~/) since OS X
    #   puts stuff in /Users/<username> rather than /home/<username> like
    #   the linux hosts do. Messy but necessary due to how I'm doing SSH
    baseYcmd = 'export PATH="~/miniconda3/bin:$PATH";'
    baseYcmd += 'python ~/DataMaid/yvette.py'
    baseYcmd += ' '

    # Semi-infinite loop
    while runner.halt is False:
        print(idict)
        for inst in idict:
            iobj = idict[inst]
            if args.debug is True:
                print("\n%s" % ("="*11))
                print("Instrument: %s" % (inst))

            # Timeouts and stuff are handled elsewhere in here
            #   BUT! timeout must be an int >= 1 (second)
            pings, drops = alfred.pingaling.ping(iobj.host,
                                                 port=iobj.port,
                                                 timeout=3)
            ts = dt.datetime.utcnow()
            meas = ['PingResults']
            tags = {'host': iobj.host}
            fields = {'ping': pings, 'dropped': drops}
            # Construct our packet
            p = alfred.packetizer.makeInfluxPacket(meas=meas,
                                                   ts=ts, tags=tags,
                                                   fields=fields)
            if args.debug is True:
                print(p)
            # Actually write to the database to store the stuff for Grafana
            #   or whatever other thing is doing the plotting/monitoring
            dbase = alfred.idb.influxobj(dbname, connect=True)
            dbase.writeToDB(p)
            dbase.closeDB()

            # Open the SSH connection; SSHHandler creates a Persistence class
            #   (in sshConnection.py) which has some retries and timeout
            #   logic baked into it so we don't have to deal with it here
            eSSH = alfred.ssh.SSHHandler(host=iobj.host,
                                         port=iobj.port,
                                         username=iobj.user,
                                         timeout=iobj.timeout,
                                         password=iobj.password)
            eSSH.openConnection()
            time.sleep(1)
            fs = checkFreeSpace(eSSH, baseYcmd, iobj.srcdir)
            fsa = decodeAnswer(fs, debug=args.debug)
            # Now make the packet given the deserialized json answer
            meas = ['FreeSpace']
            tags = {'host': iobj.host}
            ts = dt.datetime.utcnow()
            if fsa != {}:
                fields = {'path': fsa['FreeSpace']['path'],
                          'total': fsa['FreeSpace']['total'],
                          'free': fsa['FreeSpace']['free'],
                          'percentfree': fsa['FreeSpace']['percentfree']}
                # Make the packet
                p = alfred.packetizer.makeInfluxPacket(meas=meas,
                                                       ts=ts, tags=tags,
                                                       fields=fields)
            else:
                p = []
            if args.debug is True:
                print(p)
            if p != []:
                dbase = alfred.idb.influxobj(dbname, connect=True)
                dbase.writeToDB(p)
                dbase.closeDB()

            time.sleep(3)
            eSSH.closeConnection()

            # Check to see if someone asked us to quit before continuing
            if runner.halt is True:
                print("Quit inner")
                break
            else:
                # Time to sleep between instruments
                time.sleep(10)
        # Try to bust out of this outer loop too
        if runner.halt is True:
            print("Quit outer")
            break
        else:
            # Time to sleep between whole sequences of instruments
            time.sleep(300)

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
