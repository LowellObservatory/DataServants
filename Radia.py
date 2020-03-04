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

from dataservants import radia
from ligmos.utils import classes, common, packetizer
from ligmos.workers import connSetup, workerSetup


def main():
    """
    """
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
    config, comm, args, runner = workerSetup.toServeMan(conf,
                                                        passes,
                                                        logfile,
                                                        desc=desc,
                                                        extraargs=eargs,
                                                        conftype=conftype,
                                                        logfile=True)

    # Get this PID for diagnostics
    pid = os.getpid()

    # Print the preamble of this particular instance
    #   (helpful to find starts/restarts when scanning thru logs)
    common.printPreamble(pid, config)

    # Check to see if there are any connections/objects to establish
    idbs = connSetup.connIDB(comm)

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

            # Before we can make the packet, we need to convert from
            #   the default snimpy datatypes
            valDict = radia.snmptools.convertDatatypes(valDict)

            if valDict != {}:
                # This means that we stored at least something valid,
                #   so construct a influxdb packet and store it!
                packet = packetizer.makeInfluxPacket(meas=[snmptarg],
                                                     ts=None,
                                                     tags=None,
                                                     fields=valDict)

                # Grab the relevant/specified database
                db = idbs[config[snmptarg].database]

                # Technically this is hardcoded for an influxdb db
                db.singleCommit(packet,
                                table=config[snmptarg].databasetable,
                                close=True)

            # Mini sleep between targets
            time.sleep(1)

        # Consider taking a big nap
        if runner.halt is False:
            print("Starting a big sleep")
            # Sleep for bigsleep, but in small chunks to check abort
            for _ in range(bigsleep):
                time.sleep(1)
                if runner.halt is True:
                    break

    # The above loop is exited when someone sends SIGTERM
    print("PID %d is now out of here!" % (pid))

    # The PID file will have already been either deleted/overwritten by
    #   another function/process by this point, so just give back the
    #   console and return STDOUT and STDERR to their system defaults
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__
    print("STDOUT and STDERR reset.")


if __name__ == "__main__":
    main()
