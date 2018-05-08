# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on Mon Feb 26 13:16:35 2018
#
#  @author: rhamilton

from __future__ import division, print_function, absolute_import

import sys
import datetime as dt


def makeInfluxPacket(meas='', ts=dt.datetime.utcnow(), tags={}, fields={},
                     debug=False):
    """
    Makes an InfluxDB styled packet given the measurement name, metadata tags,
    and actual fields/values to put into the database
    """
    packet = {}
    for m in meas:
        packet.update({'measurement': m})
        if tags is not None:
            if type(tags) != dict:
                print("ERROR! tags must be of type dict.")
                sys.exit(-1)
            else:
                packet.update({'tags': tags})

        if type(ts) == dt.datetime:
            # InfluxDB wants timestamps in nanoseconds from Epoch (1970/01/01)
            #   but Grafana defaults to ms precision from Epoch.
            #   influxdb-python is a little fuzzy here, so convert it ourselves
            #   (dt.datetime.utcnow() doesn't supply .tzinfo, I think, and
            #     that is what influxdb-python looks for to autoconvert)
            nsts = int(ts.timestamp() * 1e3)
        elif type(ts) == int or type(ts) == float:
            # Assume that it's right
            nsts = int(ts)
        # packet.update({'time': nsts})

        if type(fields) != dict:
            print("ERROR! fields must be of type dict.")
            sys.exit(-1)
        packet.update({'fields': fields})

    if debug is True:
        print(packet)

    return [packet]
