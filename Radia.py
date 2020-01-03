# -*- coding: utf-8 -*-
#
#   This Source Code Form is subject to the terms of the Mozilla Public
#   License, v. 2.0. If a copy of the MPL was not distributed with this
#   file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#   Created on Fri Jan 3 10:40:32 MST 2020
#
#   @author: rhamilton

from __future__ import division, print_function, absolute_import

import os
import sys
import time

from pid import PidFile, PidFileError

from dataservants import radia
from ligmos.utils import classes, common, packetizer
from ligmos.workers import connSetup, workerSetup


if __name__ == "__main__":
    # For PIDfile stuff; kindly ignore
    mynameis = os.path.basename(__file__)
    if mynameis.endswith('.py'):
        mynameis = mynameis[:-3]
    pidpath = '/tmp/'

    # Define the default files we'll use/look for. These are passed to
    #   the worker constructor (toServeMan).
    conf = './config/radia.conf'
    passes = './config/passwords.conf'
    logfile = '/tmp/radia.log'
    desc = "Radia: A SNMP Grabber"
    eargs = radia.parseargs.extraArguments
    conftype = classes.snmpTarget

    # Interval between successive runs of the polling loop (seconds)
    bigsleep = 60

    # config: dictionary of parsed config file
    # comm: common block from config file
    # args: parsed options
    # runner: class that contains logic to quit nicely
    config, comm, args, runner = workerSetup.toServeMan(mynameis, conf,
                                                        passes,
                                                        logfile,
                                                        desc=desc,
                                                        extraargs=eargs,
                                                        conftype=conftype,
                                                        logfile=True)

    try:
        with PidFile(pidname=mynameis.lower(), piddir=pidpath) as p:
            # Print the preamble of this particular instance
            #   (helpful to find starts/restarts when scanning thru logs)
            common.printPreamble(p, config)

            # Check to see if there are any connections/objects to establish
            idbs = connSetup.connIDB(comm)

            # Specify our custom listener that will really do all the work
            #   Since we're hardcoding for the DCTConsumer anyways, I'll take
            #   a bit shortcut and hardcode for the DCT influx database.
            # TODO: Figure out a way to create a dict of listeners specified
            #   in some creative way. Could add a configuration item to the
            #   file and then loop over it, and change connAMQ accordingly.
            dctdb = idbs['database-dct']

            # Set up the different SNMP (snimpy) managers for the devices...
            #   Do this here outside the main loop so we're not always
            #   loading MIBs from disk and parsing them every time
            smans = {}
            for snmptarg in config:
                # snmptarg will be the *key* from a config file section!
                snmpManager = radia.snmptools.setupSNMPTarget(config[snmptarg],
                                                              loadMIBs=True)
                smans.update({snmptarg: snmpManager})

            # Semi-infinite loop
            while runner.halt is False:
                # Loop over the defined SNMP targets in the config file
                for snmptarg in config:
                    print(snmptarg)
                    valDict = radia.snmptools.grabEndpoints(smans[snmptarg],
                                                            config[snmptarg])

                    if valDict != {}:
                        # This means that we stored at least something valid,
                        #   so construct a influxdb packet and store it!
                        print(valDict)
                        packet = packetizer.makeInfluxPacket(meas=snmptarg,
                                                             ts=None,
                                                             tags=None,
                                                             fields=valDict)
                        print(packet)

                    # Mini sleep between targets
                    time.sleep(1)

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
        common.nicerExit()
