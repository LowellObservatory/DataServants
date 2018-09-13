# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 20 Aug 2018
#
#  @author: rhamilton

from __future__ import division, print_function, absolute_import

import os
import sys
import time
import signal
import datetime as dt

import logging
import logging.config
try:
    logging.config.fileConfig('stomp.log.conf')
except:
    pass

from ligmos import utils
from ligmos import workers


if __name__ == "__main__":
    log = logging.getLogger('stomp.py')
    bigsleep = 10
    # brokerhost = "10.11.131.241"
    brokerhost = 'joe.lowell.edu'
    brokerport = 61613

    # ActiveMQ connection checker
    conn = None

    crackers = utils.amq.ParrotSubscriber()

    statsRequest = 'ActiveMQ.Statistics.Broker'
    statsAnswer = '/queue/stats.broker'

    # Collect the activemq topics that are desired
    alltopics = [statsRequest, statsAnswer]

    # Establish connections and subscriptions w/our helper
    # TODO: Figure out how to fold in broker passwords
    print("Connecting to %s" % (brokerhost))
    conn = utils.amq.amqHelper(brokerhost,
                               topics=alltopics,
                               user=None,
                               passw=None,
                               port=brokerport,
                               connect=False)

    # Semi-infinite loop
    try:
        while True:
            # Double check that the broker connection is still up
            #   NOTE: conn.connect() handles ConnectionError exceptions
            if conn.conn is None:
                print("No connection at all! Retrying...")
                conn.connect()
            elif conn.conn.transport.connected is False:
                # Added the "first" flag to take care of a weird bug
                print("Connection died! Reestablishing...")
                conn.connect()
            else:
                print("Connection still valid")

            # If we're here, we made it once thru. The above comparison
            #   will fail without this and we'll never reconnect!
            first = False
            conn.publish(statsRequest, "", replyto=statsAnswer, debug=False)

            print("Starting a big sleep")
            # Sleep for bigsleep, but in small chunks to check abort
            for i in range(bigsleep):
                time.sleep(1)
    except:
        # A bit sloppy to catch control-C in the laziest way
        # Disconnect from the ActiveMQ broker
        conn.disconnect()
        print("Really disconnected from %s" % (brokerhost))
