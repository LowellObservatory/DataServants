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

Abu is designed to gather information/data from somewhere, and
repackage/republish it in a much more friendly and useful format.

The actual *storage* of data is still relegated to "Iago" to
keep things at least a little consistent on that front.
"""

from __future__ import division, print_function, absolute_import

import os
import sys
import time

from datetime import datetime as dt
from requests.exceptions import ConnectionError as RCE

import pytz

from ligmos.utils import amq, classes, common
from ligmos.workers import connSetup, workerSetup

from dataservants.abu import parseargs
from dataservants.abu.http import webgetter
from dataservants.abu.actions import parseColumbia, prepWU
from dataservants.abu.actions import parseMeteobridge, parseiSense


def main():
    """
    """
    # Define the default files we'll use/look for. These are passed to
    #   the worker constructor (toServeMan).
    conf = './config/abu.conf'
    passes = './config/passwords.conf'
    logfile = '/tmp/abu.log'
    desc = "Abu: The Kleptomaniac Scraper"
    eargs = parseargs.extraArguments
    conftype = classes.sneakyTarget

    # Interval between successive runs of the polling loop (seconds)
    bigsleep = 120

    # Quick renaming to keep line length under control

    # config: dictionary of parsed config file
    # comm: common block from config file
    # args: parsed options
    # runner: class that contains logic to quit nicely
    config, comm, _, runner = workerSetup.toServeMan(conf,
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
    # idbs = connSetup.connIDB(comm)

    amqlistener = amq.silentSubscriber()
    amqtopics = amq.getAllTopics(config, comm)
    amqs = connSetup.connAMQ(comm, amqtopics, amqlistener=amqlistener)

    # Semi-infinite loop
    while runner.halt is False:
        amqs = amq.checkConnections(amqs, subscribe=True)

        # Actually do our actions
        for sect in config:
            sObj = config[sect]
            if sObj.resourcemethod.lower() in ['http', 'https']:
                connObj = amqs[sObj.broker][0]
                try:
                    # The timekeeping on these weather servers I'm pulling
                    #   from is absolutely awful, so just use my server time
                    #   since it won't be minutes off
                    now = dt.now().astimezone(pytz.UTC)
                    wxml = webgetter(sObj.resourcelocation,
                                     user=sObj.user,
                                     pw=sObj.password)
                except RCE:
                    print("Connection error! %s" % (sect))
                    print("Moving on, hope it's temporary")
                    wxml = ''

                if wxml != '':
                    bxml = None
                    if sect in ['ldtweather', 'mesaweather']:
                        bxml, val = parseColumbia(wxml, returnDict=True)
                    elif sect == 'ldtigrid':
                        bxml = parseiSense(wxml, rootKey="ldtiSense")
                    elif sect == 'mhmeteobridge':
                        # NOTE: This will return a dict of XML packets
                        #   so it can easily be cross-posted to multiple
                        #   broker topics and then auto-parsed by iago!
                        #   This is because each metric has its own timestamp
                        #   that can differ by quite a bit (a few minutes)
                        #   depending on the RF link and the station itself
                        bxml = parseMeteobridge(wxml, stationName="MHClark",
                                                stationType="DavisVantagePro2")
                    else:
                        print("WARNING: NO BROKER FUNCTION FOUND FOR %s" %
                              (sect))

                    if bxml is not None:
                        if sObj.onlinepush is not None:
                            try:
                                pushConfig = comm[sObj.onlinepush]
                            except KeyError:
                                print("INVALID ONLINE PUSH DATA")
                                print("CHECK CONFIG FILE")
                            if pushConfig.type.lower() == "weatherunderground":
                                # We give our timestamp to make sure it
                                #   gets to WUnderground ok
                                url, payload = prepWU(pushConfig, val,
                                                      tstamp=now)
                                try:
                                    webgetter(url, params=payload)
                                except Exception as err:
                                    print(str(err))
                                    print(url, payload)

                        # The meteobridge parser returns a dict of XML packets
                        #   where the keys are to be postfixed to the base
                        #   publication topic given in the configuration file
                        if isinstance(bxml, dict) and bxml != {}:
                            for xp in bxml.keys():
                                particularTopic = "%s.%s" % (sObj.pubtopic, xp)
                                print("Sending to %s" % (particularTopic))
                                connObj.publish(particularTopic, bxml[xp])
                        else:
                            print("Sending to %s" % (sObj.pubtopic))
                            connObj.publish(sObj.pubtopic, bxml)

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
