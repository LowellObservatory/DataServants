# -*- coding: utf-8 -*-
"""
  This Source Code Form is subject to the terms of the Mozilla Public
  License, v. 2.0. If a copy of the MPL was not distributed with this
  file, You can obtain one at http://mozilla.org/MPL/2.0/.

  Created on Fri Mar 2 15:35:35 GMT+7 2018

  @author: rhamilton
"""

from __future__ import division, print_function, absolute_import

import json
import datetime as dt

from .. import utils


def actionLook(eSSH, iobj, baseYcmd, age=2, debug=False):
    """
    """
    nd = lookForNewDirectories(eSSH, baseYcmd, iobj.srcdir,
                               iobj.dirmask, age=age, debug=debug)

    return nd


def actionPing(iobj, dbname=None, debug=False):
    """
    """
    # Timeouts and stuff are handled elsewhere in here
    #   BUT! timeout must be an int >= 1 (second)
    pings, drops = utils.pingaling.ping(iobj.host,
                                        port=iobj.port,
                                        timeout=3)
    ts = dt.datetime.utcnow()
    meas = ['PingResults']
    tags = {'host': iobj.host}
    fs = {'ping': pings, 'dropped': drops}
    # Construct our packet
    packet = utils.packetizer.makeInfluxPacket(meas=meas,
                                               ts=ts,
                                               tags=tags,
                                               fields=fs)

    if debug is True:
        print(packet)
    if packet != []:
        if dbname is not None:
            # Actually write to the database to store for plotting
            dbase = utils.database.influxobj(dbname, connect=True)
            dbase.writeToDB(packet)
            dbase.closeDB()
    return packet


def actionSpace(eSSH, iobj, baseYcmd, dbname=None, debug=False):
    """
    """
    fs = checkFreeSpace(eSSH, baseYcmd, iobj.srcdir)
    fsa = decodeAnswer(fs, debug=debug)
    # Now make the packet given the deserialized json answer
    meas = ['FreeSpace']
    tags = {'host': iobj.host}
    ts = dt.datetime.utcnow()
    if fsa != {}:
        fs = {'path': fsa['FreeSpace']['path'],
              'total': fsa['FreeSpace']['total'],
              'free': fsa['FreeSpace']['free'],
              'percentfree': fsa['FreeSpace']['percentfree']}
        # Make the packet
        packet = utils.packetizer.makeInfluxPacket(meas=meas,
                                                   ts=ts,
                                                   tags=tags,
                                                   fields=fs)
    else:
        packet = []

    if debug is True:
        print(packet)
    if packet != []:
        if dbname is not None:
            # Actually write to the database to store for plotting
            dbase = utils.database.influxobj(dbname, connect=True)
            dbase.writeToDB(packet)
            dbase.closeDB()
    return packet


def decodeAnswer(ans, debug=False):
    final = {}
    if ans[0] == 0:
        if ans[1] != '':
            final = json.loads(ans[1])
            if debug is True:
                print(final)
    return final


def checkFreeSpace(sshConn, basecmd, sdir):
    """
    """
    fcmd = "%s -f %s" % (basecmd, sdir)
    res = sshConn.sendCommand(fcmd)

    return res


def lookForNewDirectories(sshConn, basecmd, sdir, dirmask, age=2, debug=False):
    """
    """
    fcmd = "%s -l %s -r %s --rangeNew %d" % (basecmd, sdir, dirmask, age)
    res = sshConn.sendCommand(fcmd, debug=debug)

    return res
