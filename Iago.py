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

from pid import PidFile, PidFileError

from ligmos import utils
from ligmos import workers
from dataservants import iago


if __name__ == "__main__":
    # For PIDfile stuff; kindly ignore
    mynameis = os.path.basename(__file__)
    if mynameis.endswith('.py'):
        mynameis = mynameis[:-3]
    pidpath = '/tmp/'

    # Define the default files we'll use/look for. These are passed to
    #   the worker constructor (toServeMan).
    conf = './iago.conf'
    passes = './passwords.conf'
    logfile = '/tmp/iago.log'
    desc = "Iago: The ActiveMQ Parrot"
    eargs = iago.parseargs.extraArguments

    # Interval between successive runs of the polling loop (seconds)
    bigsleep = 120

    # Quick renaming to keep line length under control
    malarms = utils.multialarm
    ip = utils.packetizer
    ic = utils.classes.snoopTarget
    udb = utils.database
    amqp = iago.amqparse

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

    # ActiveMQ connection checker
    conn = None

    try:
        with PidFile(pidname=mynameis.lower(), piddir=pidpath) as p:
            # Print the preamble of this particular instance
            #   (helpful to find starts/restarts when scanning thru logs)
            utils.common.printPreamble(p, idict)

            if cblk.dbtype is not None and cblk.dbtype.lower() == 'influxdb':
                # Create an influxdb object that can be spread around to
                #   connect and commit packets when they're created.
                #   Leave it disconnected initially.
                idb = udb.influxobj(cblk.dbname,
                                    host=cblk.dbhost,
                                    port=cblk.dbport,
                                    user=cblk.dbuser,
                                    pw=cblk.dbpass,
                                    connect=False)

                # Connect to check the retention policy, then disconnect
                #   but keep the object.
                idb.connect()
                # Set the retention to default (see ligmos/utils/database.py)
                idb.alterRetention()
                idb.disconnect()
            else:
                # No other database types are defined yet
                idb = None

            crackers = None
            if cblk is not None and cblk.brokertype.lower() == "activemq":
                # Register the custom listener class that Iago has.
                #   This will be the thing that parses packets depending
                #   on their topic name and does the hard stuff!!
                crackers = amqp.DCTConsumer(dbconn=idb)

            conn, crackers = utils.amq.setupBroker(idict, cblk, ic,
                                                   listener=crackers)

            # Semi-infinite loop
            while runner.halt is False:

                # Double check that the broker connection is still up
                #   NOTE: conn.connect() handles ConnectionError exceptions
                if conn.conn is None:
                    print("No connection at all! Retrying...")
                    conn.connect(listener=crackers)
                elif conn.conn.transport.connected is False:
                    print("Connection died! Reestablishing...")
                    conn.connect(listener=crackers)
                else:
                    print("Connection still valid")

                # Consider taking a big nap
                if runner.halt is False:
                    print("Starting a big sleep")
                    # Sleep for bigsleep, but in small chunks to check abort
                    for _ in range(bigsleep):
                        time.sleep(0.5)
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
    except PidFileError:
        # We've probably already started logging, so reset things
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
        print("Already running! Quitting...")
        utils.common.nicerExit()
