# -*- coding: utf-8 -*-
#
#   This Source Code Form is subject to the terms of the Mozilla Public
#   License, v. 2.0. If a copy of the MPL was not distributed with this
#   file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#   Created on Thu Apr 19 11:41:01 GMT+7 2018
#
#   @author: rhamilton

from __future__ import division, print_function, absolute_import

import os
import sys
import time
import signal
import datetime as dt

from dataservants import iago
from dataservants import utils

from pid import PidFile, PidFileError


if __name__ == "__main__":
    # For PIDfile stuff; kindly ignore
    mynameis = os.path.basename(__file__)
    if mynameis.endswith('.py'):
        mynameis = mynameis[:-3]
    pidpath = '/tmp/'

    # InfluxDB database name to store stuff in
    dbname = 'LIGInstruments'

    # Interval between successive runs of the polling loop (seconds)
    bigsleep = 600

    # Total time for entire set of actions per instrument
    alarmtime = 600

    # idict: dictionary of parsed config file
    # args: parsed options of wadsworth.py
    # runner: class that contains logic to quit nicely
    idict, args, runner = iago.squawk.beginSquawking(procname=mynameis,
                                                     logfile=False)

    # Quick renaming to keep line length under control
    malarms = utils.multialarm

    # ActiveMQ connection checker
    conn = None

    try:
        with PidFile(pidname=mynameis.lower(), piddir=pidpath) as p:
            # Print the preamble of this particular instance
            #   (helpful to find starts/restarts when scanning thru logs)
            utils.common.printPreamble(p, idict)

            # One by one, set up the messager connections.
            #   THIS OF COURSE implies that the connections are done elsewhere
            #   in Iago's codepath; specifically iago.amqparse (etc.)
            for each in idict:
                it = idict[each]
                first = False
                if it.type.lower() == "activemq":
                    # Establish connections and subscriptions w/our helper
                    conn = iago.amqparse.amqHelper(it.host,
                                                   it.topics,
                                                   dbname=it.influxdbname,
                                                   user=None,
                                                   passw=None,
                                                   port=61613,
                                                   connect=True)
                    first = True

            # Semi-infinite loop
            while runner.halt is False:

                # Double check that the connection is still up
                #   NOTE: conn.connect() handles ConnectionError exceptions
                if conn.conn is None:
                    print("No connection at all! Retrying...")
                    conn.connect()
                elif conn.conn.transport.connected is False and first is False:
                    # Added the "first" flag to take care of a weird bug
                    print("Connection died! Reestablishing...")
                    conn.connect()
                else:
                    print("Connection still valid")

                # Consider taking a big nap
                if runner.halt is False:
                    print("Starting a big sleep")
                    # Sleep for bigsleep, but in small chunks to check abort
                    for i in range(bigsleep):
                        time.sleep(1)
                        if runner.halt is True:
                            break

            # The above loop is exited when someone sends SIGTERM
            print("PID %d is now out of here!" % (p.pid))

            # Disconnect from the ActiveMQ broker
            conn.disconnect()

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
