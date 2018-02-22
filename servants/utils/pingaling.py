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
import signal
import numpy as np

import serviceping


def calcMedian(vals):
    """
    """
#    print(vals)
    avg = np.nanmedian(vals)

    return avg


def ping(host, port=22, repeats=7, waittime=0.5, timeout=10, debug=False):
    """
    Want a decent number of pings since some hosts (like OS X) can
    take a few seconds to wake up their hard drives if they're sleeping

    Also want to give them a decent number of seconds to wake up, since
    the timeout doesn't issue an exception but does just give up
    """
    nretries = 0
    final = {}
    allret = []
    dropped = 0
    pres = []
    while nretries < repeats:
        try:
            res = serviceping.network.scan(host, port=22, timeout=timeout)
            pres.append(res['durations']['connect']*1000.)
            if debug is True:
                print(res)
        except serviceping.network.ScanFailed:
            pres.append(np.nan)
            dropped += 1
            if debug is True:
                print("Connection to host '%s' failed!" % (host))
        nretries += 1
        time.sleep(waittime)

    return pres, dropped
