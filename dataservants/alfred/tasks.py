# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 21 Mar 2018
#
#  @author: rhamilton

"""Tasks that Alfred nominally does that don't involve Yvette at all.
"""

from __future__ import division, print_function, absolute_import

import numpy as np
import datetime as dt

from ligmos import utils


def actionPing(iobj, dbname=None, debug=False):
    """Ping a remote machine and record its response.

    Pings a remote machine, recording its average response time if that
    time is within the number of seconds indicated by timeout.

    The main function called on the remote side is
    :func:`dataservants.utils.pingaling.ping`.

    Args:
        iobj (:class:`dataservants.utils.common.InstrumentHost`)
            Class containing instrument machine target information
            populated via :func:`dataservants.utils.confparsers.parseInstConf`.
        dbname (:obj:`str`, optional)
            InfluxDB database name in which to write the results. Defaults to
            None, in which case the InfluxDB packet is constructed but
            not written anywhere.
        debug (:obj:`bool`)
            Bool to trigger additional debugging outputs. Defaults to False.

    Returns:
        packet (:obj:`list` of :obj:`dicts`)
            Dictionary in the style of an InfluxDB data packet, containing
            measurement name, timestamp, tag(s), and the actual values.
            The packet's main key is :obj:`PingResults` and the values
            are in milliseconds (ms) for 'ping' and integer for 'dropped'.

            .. code-block:: python

                packet = [{'measurement': 'PingResults',
                           'tags': {'host': 'rc2'},
                           'time': datetime.datetime(2018, 3, 6,
                                                     21, 51, 49, 972034),
                           'fields': {'ping': 2.7909278869628906,
                                      'dropped': 0}}]
    """
    # In case of emergency
    superdebug = False

    # Timeouts and stuff are handled elsewhere in here
    #   BUT! timeout must be an int >= 1 (second)
    pings, drops = utils.pingaling.ping(iobj.host,
                                        port=iobj.port,
                                        timeout=3)
    ts = dt.datetime.utcnow()
    meas = ['PingResults']
    tags = {'host': iobj.host}
    # InfluxDB can only store one datatype per field, so no NaN or null
    if np.isnan(pings) is True:
        pings = -9999.
    fs = {'ping': pings, 'dropped': drops}
    # Construct our packet
    packet = utils.packetizer.makeInfluxPacket(meas=meas,
                                               ts=ts,
                                               tags=tags,
                                               fields=fs)

    if superdebug is True:
        print(packet)
    if packet != []:
        if dbname is not None:
            # Actually write to the database to store for plotting
            dbase = utils.database.influxobj(dbname, connect=True)
            dbase.writeToDB(packet)
            dbase.closeDB()
    return packet
