# -*- coding: utf-8 -*-
"""
  This Source Code Form is subject to the terms of the Mozilla Public
  License, v. 2.0. If a copy of the MPL was not distributed with this
  file, You can obtain one at http://mozilla.org/MPL/2.0/.

  Created on Wed Feb 21 14:12:11 2018

  @author: rhamilton
"""

from __future__ import division, print_function, absolute_import

import time
import numpy as np

import serviceping
from . import alarms


def calcMedian(vals):
    """
    """
#    print(vals)
    avg = np.nanmedian(vals)

    return avg


def ping(host, port=22, repeats=7, waittime=0.5, timeout=1, debug=False):
    """
    Want a decent number of pings since some hosts (like OS X) can
    take a few seconds to wake up their hard drives if they're sleeping

    Also want to give them a decent number of seconds to wake up, since
    the timeout doesn't issue an exception but does just give up
    """
    nretries = 0
    dropped = 0
    pres = []
    while nretries < repeats:
        try:
            alarms.setAlarm(timeout=timeout)
            res = serviceping.network.scan(host, port=22, timeout=timeout)
            alarms.clearAlarm()

            pres.append(res['durations']['connect']*1000.)
            if debug is True:
                print(res)
        except alarms.TimeoutException as err:
            print("Timed out: %s" % (str(err)))
            dropped += 1
            pres.append(np.nan)
        except serviceping.network.ScanFailed as err:
            pres.append(np.nan)
            dropped += 1
            if debug is True:
                print("Connection to host '%s' failed!" % (host))
                print(str(err))
        nretries += 1
        time.sleep(waittime)

    return pres, dropped
