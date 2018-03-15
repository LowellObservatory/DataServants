# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 6 Mar 2018
#
#  @author: rhamilton

from __future__ import division, print_function, absolute_import

import os
import psutil


def checkLoadAvgs():
    """
    """
    res = os.getloadavg()
    ans = {'Avg1Min': res[0],
           'Avg5Min': res[1],
           'Avg15Min': res[2]}

    return ans


def checkCPUusage():
    """
    """
    # NOTE: interval MUST be > 0.1s otherwise it'll give garbage results
    res = psutil.cpu_times_percent(interval=1.0)

    # At this point res is a namedtuple type, so we need to dance a little bit
    #   (_asdict() is a builtin method and _fields is a builtin property)
    ans = {}
    rd = res._asdict()
    for each in res._fields:
        ans.update({each: rd[each]})

    return ans


def checkMemStats():
    """
    """
    res = psutil.virtual_memory()

    # See above; same dance routine
    ans = {}
    rd = res._asdict()
    for each in res._fields:
        # Just go ahead and put the values from bytes to GiB
        ans.update({each: rd[each]/1024./1024./1024.})

    # One last one to help plotting
    ans.update({"percent": ans["available"]/ans["total"]})

    return ans
