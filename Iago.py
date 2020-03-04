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

from dataservants import iago
from ligmos.workers import connSetup, workerSetup
from ligmos.utils import amq, classes, common


def main():
    """
    """
    # Define the default files we'll use/look for. These are passed to
    #   the worker constructor (toServeMan).
    conf = './config/iago.conf'
    passes = './config/passwords.conf'
    logfile = '/tmp/iago.log'
    desc = "Iago: The ActiveMQ Parrot"
    eargs = iago.parseargs.extraArguments
    conftype = classes.snoopTarget

    # Interval between successive runs of the polling loop (seconds)
    bigsleep = 120

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

    # Specify our custom listener that will really do all the work
    #   Since we're hardcoding for the DCTConsumer anyways, I'll take
    #   a bit shortcut and hardcode for the DCT influx database.
    # TODO: Figure out a way to create a dict of listeners specified
    #   in some creative way. Could add a configuration item to the
    #   file and then loop over it, and change connAMQ accordingly.
    dctdb = idbs['database-dct']
    dctdb.tablename = config['dctbroker'].tablename
    amqlistener = iago.listener.DCTConsumer(dbconn=dctdb)
    amqtopics = amq.getAllTopics(config, comm)
    amqs = connSetup.connAMQ(comm, amqtopics, amqlistener=amqlistener)

    # Check to see if there are any connections/objects to establish
    amqtopics = amq.getAllTopics(config, comm)

    # Semi-infinite loop
    while runner.halt is False:
        # Check on our connections
        amqs = amq.checkConnections(amqs, subscribe=True)

        # There really isn't anything to actually *do* in here;
        #   all the real work happens in the listener, so we really
        #   just spin our wheels here.

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

    # Disconnect from all ActiveMQ brokers
    amq.disconnectAll(amqs)

    # The PID file will have already been either deleted/overwritten by
    #   another function/process by this point, so just give back the
    #   console and return STDOUT and STDERR to their system defaults
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__
    print("STDOUT and STDERR reset.")

if __name__ == "__main__":
    main()
