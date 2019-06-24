# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 22 Aug 2018
#
#  @author: rhamilton

"""Abu: The Kleptomaniac Monkey

Abu is designed to live on all machines of interest, and
pull information from a variety of log file sources and republish them
in a more friendly format.  A close friend of "Iago" in that sense.

There can only be one Abu instance running on a given machine,
controlled via a PID file in /tmp/ as well as some command line options to
kill/restart the Abu process.
"""

from __future__ import division, print_function, absolute_import

import os
import sys
import time

from pid import PidFile, PidFileError

from dataservants import abu
from ligmos.utils import amq, classes, common
from ligmos.workers import connSetup, workerSetup


def main():
    """
    """
    # For PIDfile stuff; kindly ignore
    mynameis = os.path.basename(__file__)
    if mynameis.endswith('.py'):
        mynameis = mynameis[:-3]
    pidpath = '/tmp/'

    # Define the default files we'll use/look for. These are passed to
    #   the worker constructor (toServeMan).
    conf = './abu.conf'
    passes = './passwords.conf'
    logfile = '/tmp/abu.log'
    desc = "Abu: The Kleptomaniac Scraper"
    eargs = abu.parseargs.extraArguments
    conftype = classes.sneakyTarget

    # Interval between successive runs of the polling loop (seconds)
    bigsleep = 120

    # Quick renaming to keep line length under control

    # config: dictionary of parsed config file
    # comm: common block from config file
    # args: parsed options
    # runner: class that contains logic to quit nicely
    config, comm, _, runner = workerSetup.toServeMan(mynameis, conf,
                                                     passes,
                                                     logfile,
                                                     desc=desc,
                                                     extraargs=eargs,
                                                     conftype=conftype,
                                                     logfile=False)

    try:
        with PidFile(pidname=mynameis.lower(), piddir=pidpath) as p:
            # Print the preamble of this particular instance
            #   (helpful to find starts/restarts when scanning thru logs)
            common.printPreamble(p, config)

            # Check to see if there are any connections/objects to establish
            amqlistener = amq.silentSubscriber()

            amqtopics = amq.getAllTopics(config, comm)
            amqs, idbs = connSetup.connAMQ_IDB(comm, amqtopics,
                                               amqlistener=amqlistener)

            # Semi-infinite loop
            while runner.halt is False:
                amqs = amq.checkConnections(amqs, subscribe=True)

                # Actually do our actions
                for sect in config:
                    # A bit of messy hacking to cut to the chase
                    #   Should eventually turn this into a proper action/method
                    if sect.lower() == 'dctweather':
                        sObj = config[sect]
                        connObj = amqs[sObj.broker][0]
                        if sObj.resourcemethod.lower() == 'http' or 'https':
                            wxml = abu.http.webgetter(sObj.resourcelocation)
                            if wxml != '':
                                bxml = abu.actions.columbiaTranslator(wxml)
                                print("Sending to %s" % (sObj.pubtopic))
                                connObj.publish(sObj.pubtopic, bxml)

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

            # Disconnect from all ActiveMQ brokers
            amq.disconnectAll(amqs)

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


if __name__ == "__main__":
    main()
