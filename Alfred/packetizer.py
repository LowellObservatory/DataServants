# -*- coding: utf-8 -*-
"""
  This Source Code Form is subject to the terms of the Mozilla Public
  License, v. 2.0. If a copy of the MPL was not distributed with this
  file, You can obtain one at http://mozilla.org/MPL/2.0/.

  Created on Mon Feb 26 13:16:35 2018

  @author: rhamilton
"""

from __future__ import division, print_function, absolute_import

import sys
import datetime as dt


def makeInfluxPacket(meas='', ts=dt.datetime.now(), tags={}, fields={},
                     debug=False):
    """
    Makes an InfluxDB styled packet given the measurement name, metadata tags,
    and actual fields/values to put into the database
    """
    packet = {}
    for m in meas:
        packet.update({'measurement': m})
        if type(tags) != dict:
            print("ERROR! tags must be of type dict.")
            sys.exit(-1)
        else:
            packet.update({'tags': tags})
        packet.update({'time': ts})
        if type(fields) != dict:
            print("ERROR! fields must be of type dict.")
            sys.exit(-1)
        packet.update({'fields': fields})

    if debug is True:
        print(packet)

    return [packet]
