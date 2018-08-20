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

from ligmos import utils
from ligmos import workers
from dataservants import iago

from pid import PidFile, PidFileError


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
    bigsleep = 600

    # Total time for entire set of actions per instrument
    alarmtime = 600

    # Quick renaming to keep line length under control
    malarms = utils.multialarm
    ip = utils.packetizer
    ic = utils.common.snoopTarget
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

            if cblk.dbtype.lower() == 'influxdb':
                # Create an influxdb object that can be spread around to
                #   connect and commit packets when they're created.
                #   Leave it disconnected initially.
                # TODO: Figure out how to fold in database passwords
                idb = udb.influxobj(cblk.dbname,
                                    host=cblk.dbhost,
                                    port=cblk.dbport,
                                    user=cblk.dbuser,
                                    pw=None,
                                    connect=False)
            else:
                # No other database types are defined yet
                pass

            if cblk.brokertype.lower() == "activemq":
                # Register the custom listener class that Iago has.
                #   This will be the thing that parses packets depending
                #   on their topic name and does the hard stuff!!
                crackers = amqp.DCTSubscriber(dbconn=idb)
            else:
                # No other broker types are defined yet
                pass

            # Collect the activemq topics that are desired
            alltopics = []
            for each in idict:
                it = idict[each]
                alltopics.append(it.topics)

            # Flatten the topic list (only good for 2D)
            alltopics = [val for sub in alltopics for val in sub]

            # Establish connections and subscriptions w/our helper
            # TODO: Figure out how to fold in broker passwords
            print("Connecting to %s" % (cblk.brokerhost))
            conn = utils.amq.amqHelper(cblk.brokerhost,
                                       topics=alltopics,
                                       user=cblk.brokeruser,
                                       passw=None,
                                       port=cblk.brokerport,
                                       connect=False,
                                       listener=crackers)

            # Semi-infinite loop
            while runner.halt is False:

                # Double check that the broker connection is still up
                #   NOTE: conn.connect() handles ConnectionError exceptions
                if conn.conn is None:
                    print("No connection at all! Retrying...")
                    conn.connect(listener=crackers)
                elif conn.conn.transport.connected is False:
                    # Added the "first" flag to take care of a weird bug
                    print("Connection died! Reestablishing...")
                    conn.connect(listener=crackers)
                else:
                    print("Connection still valid")

                # If we're here, we made it once thru. The above comparison
                #   will fail without this and we'll never reconnect!
                first = False

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
