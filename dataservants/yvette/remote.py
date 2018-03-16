# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on Fri Mar 2 15:35:35 GMT+7 2018
#
#  @author: rhamilton

"""Yvette actions, to link remote calls with locally running functions.

action* functions provide the interface between the command line and the
lower level routines internal to Yvette that actually do the work
(such as :mod:`dataservants.utils.files` or :mod:`dataservants.utils.cpumem`).
"""

from __future__ import division, print_function, absolute_import

import time
import json
import numpy as np
import datetime as dt

from .. import utils


def actionBase(eSSH, iobj, baseYcmd, func, *args, **kwargs):
    """
    """
    pass


def actionLook(eSSH, iobj, baseYcmd, age=2, debug=False):
    """Look for directories matching a specified format younger than X days old.

    Uses a `Paramiko <http://docs.paramiko.org/en/latest/>`_ SSH
    connection to execute commands to a :obj:`dataservants.yvette` instance
    running on a remote target machine.

    The main function called on the remote side is
    :func:`dataservants.utils.files.getDirListing`.

    Args:
        eSSH (:class:`dataservants.utils.ssh.SSHHandler`)
            Class describing parameters needed to open SSH connection to
            instantiated class's host.
        iobj (:class:`dataservants.utils.common.InstrumentHost`)
            Class containing instrument machine target information
            populated via :func:`dataservants.utils.confparsers.parseInstConf`.
        baseYcmd (:obj:`str`)
            String describing how to properly start Yvette on the target.
            Should include any necessary EXPORT statements before calling
            python to take care of any environment problems.
        age (:obj:`int`, optional)
            Age in days to consider a directory 'new' and return its path.
            Defaults to 2.
        debug (:obj:`bool`)
            Bool to trigger additional debugging outputs. Defaults to False.

    Returns:
        fnd (:obj:`dict`)
            Dictionary of results, containing a single key :obj:`DirsNew`
            linked to a list of directories newer/younger than :obj:`age`.

            .. code-block:: python

                fnd = {"DirsNew":
                       ["/mnt/lemi/lois/20180305a",
                        "/mnt/lemi/lois/20180306a"]}
    """
    fcmd = "%s -l %s -r %s --rangeNew %d" % (baseYcmd,
                                             iobj.srcdir,
                                             iobj.dirmask,
                                             age)
    nd = eSSH.sendCommand(fcmd, debug=debug)

    fnd = decodeAnswer(nd)

    return fnd


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


def actionSpace(eSSH, iobj, baseYcmd, dbname=None, debug=False):
    """Check free space at the specified directory.

    Uses a `Paramiko <http://docs.paramiko.org/en/latest/>`_ SSH
    connection to execute commands to a :obj:`dataservants.yvette` instance
    running on a remote target machine.

    The main function called on the remote side is
    :func:`dataservants.utils.files.checkFreeSpace`.

    Args:
        eSSH (:class:`dataservants.utils.ssh.SSHHandler`)
            Class describing parameters needed to open SSH connection to
            instantiated class's host.
        iobj (:class:`dataservants.utils.common.InstrumentHost`)
            Class containing instrument machine target information
            populated via :func:`dataservants.utils.confparsers.parseInstConf`.
        baseYcmd (:obj:`str`)
            String describing how to properly start Yvette on the target.
            Should include any necessary EXPORT statements before calling
            python to take care of any environment problems.
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
            The packet's main key is :obj:`FreeSpace` and the values
            are in `GiB <https://en.wikipedia.org/wiki/Gibibyte>`_
            (2**30 bytes == 1 GiB) to prevent 32-bit integer overflows
            that were occuring when doing math with the original values
            reported by :func:`os.statvfs` in bytes.

            .. code-block:: python

                packet = [{'measurement': 'FreeSpace',
                           'tags': {'host': 'rc1'},
                           'time': datetime.datetime(2018, 3, 6,
                                                     21, 51, 30, 255864),
                           'fields': {'path': '/data/lois/dct/gwaves',
                                      'total': 402.3735809326172,
                                      'free': 268.3059501647949,
                                      'percentfree': 0.67}}]
    """
    # In case of emergency
    superdebug = False

    fcmd = "%s -f %s" % (baseYcmd, iobj.srcdir)
    fs = eSSH.sendCommand(fcmd)
    # Timestamp of when this all (just) occured
    ts = dt.datetime.utcnow()

    # Turn Yvette's JSON answer into an object
    fsa = decodeAnswer(fs, debug=debug)

    # Now make the packet given the deserialized json answer
    meas = ['FreeSpace']
    tags = {'host': iobj.host}
    # Fields from Yvette's answer that we want to record
    #   Looks a bit more complicated since it's a dict that gives
    #   databasekey: YvetteAnswerKey
    desired = ['path', 'total', 'free', 'percentfree']
    gf = {}
    if fsa != {}:
        for each in desired:
            try:
                gf.update({each: fsa['FreeSpace'][each]})
            except KeyError:
                pass

        # fs = {'path': fsa['FreeSpace']['path'],
        #       'total': fsa['FreeSpace']['total'],
        #       'free': fsa['FreeSpace']['free'],
        #       'percentfree': fsa['FreeSpace']['percentfree']}

        # Make the packet
        packet = utils.packetizer.makeInfluxPacket(meas=meas,
                                                   ts=ts,
                                                   tags=tags,
                                                   fields=gf)
    else:
        packet = []

    if superdebug is True:
        print(packet)
    if packet != []:
        if dbname is not None:
            # Actually write to the database to store for plotting
            dbase = utils.database.influxobj(dbname, connect=True)
            dbase.writeToDB(packet)
            dbase.closeDB()
    return packet


def actionStats(eSSH, iobj, baseYcmd, dbname=None, debug=False):
    """Check CPU and RAM information on the remote machine.

    Uses a `Paramiko <http://docs.paramiko.org/en/latest/>`_ SSH
    connection to execute commands to a :obj:`dataservants.yvette` instance
    running on a remote target machine.

    The main function called on the remote side is
    :func:`dataservants.utils.files.checkFreeSpace`.

    Args:
        eSSH (:class:`dataservants.utils.ssh.SSHHandler`)
            Class describing parameters needed to open SSH connection to
            instantiated class's host.
        iobj (:class:`dataservants.utils.common.InstrumentHost`)
            Class containing instrument machine target information
            populated via :func:`dataservants.utils.confparsers.parseInstConf`.
        baseYcmd (:obj:`str`)
            String describing how to properly start Yvette on the target.
            Should include any necessary EXPORT statements before calling
            python to take care of any environment problems.
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
            The packet's main key is :obj:`MachineStats` and the values
            are in percent (0-1) for the CPU stats and in
            `GiB <https://en.wikipedia.org/wiki/Gibibyte>`_ for the memory
            stats.

            .. code-block:: python

                packet = [{'measurement': 'MachineStats',
                           'tags': {'host': 'rc2'},
                           'time': datetime.datetime(2018, 3, 6,
                                                     21, 38, 38, 581119),
                           'fields': {'cpuUser': 0.5,
                                      'cpuSys': 0.5,
                                      'cpuIdle': 97.5,
                                      'cpuIO': 1.5,
                                      'memTotal': 3.828460693359375,
                                      'memAvail': 2.8249664306640625,
                                      'memActive': 2.1589126586914062,
                                      'memPercent': 0.7378857083642218}}]


    .. note::
        OS X does not support or report 'iowait' so this statistic will
        be unavailable on those remote machines.
    """
    # In case of emergency
    superdebug = False

    fcmd = "%s --cpumem" % (baseYcmd)
    fs = eSSH.sendCommand(fcmd, debug=debug)
    # Timestamp of when this all (just) occured
    ts = dt.datetime.utcnow()

    # Turn Yvette's JSON answer into an object
    fsa = decodeAnswer(fs, debug=debug)

    # Now make the packet given the deserialized json answer
    meas = ['MachineStats']
    tags = {'host': iobj.host}
    # Fields from Yvette's answer that we want to record.
    #   Complicated because the storage tag doesn't match the returned tag
    dbmapCPU = {'cpuUser': 'user',
                'cpuSys': 'system',
                'cpuIdle': 'idle',
                'cpuIO': 'iowait'}
    dbmapLoad = {'sys1MinLoad': 'Avg1Min',
                 'sys5MinLoad': 'Avg5Min',
                 'sys15MinLoad': 'Avg15Min'}
    dbmapMem = {'memTotal': 'total',
                'memAvail': 'available',
                'memActive': 'active',
                'memPercent': 'percent'}

    gf = {}
    if fsa != {}:
        for each in dbmapCPU.keys():
            try:
                gf.update({each: fsa['MachineCPU'][dbmapCPU[each]]})
            except KeyError:
                pass

        for oach in dbmapLoad.keys():
            try:
                gf.update({each: fsa['MachineLoads'][dbmapLoad[oach]]})
            except KeyError:
                pass

        for pach in dbmapMem.keys():
            try:
                gf.update({each: fsa['MachineMem'][dbmapMem[pach]]})
            except KeyError:
                pass

        # Actually make the packet
        packet = utils.packetizer.makeInfluxPacket(meas=meas,
                                                   ts=ts,
                                                   tags=tags,
                                                   fields=gf)
    else:
        packet = []

    if superdebug is True:
        print(gf)
        print(packet)
    if packet != []:
        if dbname is not None:
            # Actually write to the database to store for plotting
            dbase = utils.database.influxobj(dbname, connect=True)
            dbase.writeToDB(packet, debug=True)
            dbase.closeDB()
    return packet


def decodeAnswer(ans, debug=False):
    """Parse the JSON formatted output from Yvette.

    Yvette's main code :func:`dataservants.yvette.tidy.beginTidying` returns
    both the return value and the result in a JSON formatted response.  Given
    that JSON result, parse it and return just the answer if the return value
    was 0 indicating a successfully completed request.

    Args:
        ans (:obj:`json`)
            JSON formatted response from Yvette
        debug (:obj:`bool`)
            Bool to trigger additional debugging outputs. Defaults to False.
    Returns:
        final (:obj:`dict`)
            Dict formatted answer from Yvette, parsed only if the return
            status (ans[0]) was success (0) and the result (ans[1])
            isn't an empty str.
    """
    final = {}
    if ans[0] == 0:
        if ans[1] != '':
            final = json.loads(ans[1])
            if debug is True:
                print(final)
    return final
