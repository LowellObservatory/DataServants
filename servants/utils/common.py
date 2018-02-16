# -*- coding: utf-8 -*-
"""
  This Source Code Form is subject to the terms of the Mozilla Public
  License, v. 2.0. If a copy of the MPL was not distributed with this
  file, You can obtain one at http://mozilla.org/MPL/2.0/.

  Created on Thu Feb 15 16:58:53 2018

  @author: rhamilton
"""

from __future__ import division, print_function, absolute_import

import datetime as dt
from os.path import basename


def dateDiff(fstr, debug=False):
    """
    """
    dstr = basename(fstr)
    dtobj = strToDate(dstr)
    dtts = dt.datetime.timestamp(dtobj)
    now = dt.datetime.timestamp(dt.datetime.utcnow())
    diff = (now - dtts)

    if debug is True:
        print(dtobj, dtts, now, diff)

    return diff


def strToDate(st):
    """
    """
    # Try just the first 8 characters (20180214, 20180214a, 20180214_junk)
    dted = None
    try:
        dted = dt.datetime.strptime(st[0:8], "%Y%m%d")
    except ValueError:
        # Try some other ones
        if len(st) == 10:
            try:
                dted = dt.datetime.strptime(st, "%Y-%m-%d")
            except ValueError:
                pass

    return dted
