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

from ligmos import utils


def rStringVerify(baseYcmd, ldir, filetype):
    fcmd = "%s --verify %s --filetype %s" % (baseYcmd, ldir, filetype)
    return fcmd


def rStringLookNew(baseYcmd, bdir, dirmask, newage=2):
    fcmd = "%s -l %s -r %s --rangeNew %d" % (baseYcmd,
                                             bdir,
                                             dirmask,
                                             newage)
    return fcmd


def rStringLookOld(baseYcmd, bdir, dirmask, newage=2, oldage=365):
    fcmd = "%s -o %s -r %s --rangeOld %d --oldest %d" % (baseYcmd,
                                                         bdir,
                                                         dirmask,
                                                         newage, oldage)
    return fcmd


def rStringCheckProcess(baseYcmd, name='lois'):
    fcmd = "%s --checkProcess %s" % (baseYcmd, name)
    return fcmd


def rStringSpace(baseYcmd, mdir):
    fcmd = "%s -f %s" % (baseYcmd, mdir)
    return fcmd


def rStringStats(baseYcmd):
    fcmd = "%s --cpumem" % (baseYcmd)
    return fcmd


def commandYvetteSimple(eSSH, baseYcmd, args, iobj, cmd, debug=False):
    """
    A simplifier to cut down on copy-and-paste-itis for commands that
    don't need extra processing to store results

        In this case, the return value from Yvette will look like this:
        .. code-block:: python

            fnd = {"DirsNew":
                    (2, ["/mnt/lemi/lois/20180305a",
                    "/mnt/lemi/lois/20180306a"])}
    """
    # Make comparisons a bit easier
    cmd = cmd.lower()

    # Command menu
    if cmd == 'findnew':
        fcmd = rStringLookNew(baseYcmd, iobj.srcdir, iobj.dirmask,
                              newage=args.rangeNew)
    elif cmd == 'findold':
        fcmd = rStringLookOld(baseYcmd, iobj.srcdir, iobj.dirmask,
                              newage=args.rangeOld, oldage=args.oldest)
    elif cmd == 'verify':
        fcmd = rStringVerify(baseYcmd, iobj.srcdir, iobj.filemask)
    else:
        print("Command unknown! Ignoring.")
        return None

    # If we got here, the command is valid so we'll send it
    nd = eSSH.sendCommand(fcmd, debug=debug)
    print(nd)
    fnd = decodeAnswer(nd)

    return fnd


def actionProcess(eSSH, baseYcmd, iobj, procName='lois',
                  db=None, debug=False):
    """
    """
    # A place to store any/all packets that are made here, to be returned
    packets = []

    # Get the command string that Yvette will understand and then send it
    fcmd = rStringCheckProcess(baseYcmd, name=procName)
    fs = eSSH.sendCommand(fcmd)

    # Timestamp of when this all (just) occured
    ts = dt.datetime.utcnow()

    # Turn Yvette's JSON answer into an object
    fsa = decodeAnswer(fs, debug=debug)

    # Now make the packet given the deserialized json answer
    meas = ['ProcessStats']
    tags = {'host': iobj.host}

    # Define some extra tags that we use to show overall status in Grafana.
    #   Can't depend on presence of packet in the db because the query
    #   interval depends a little bit on current time and it's easy to get
    #   false positives in the dashboard. CUSTOM.
    # etags = ['binLOIS', 'scriptLOIS', 'generic']

    # Fields from Yvette's answer that we want to record as a status packet.
    desired = ['boottime', 'hostname']

    # Make and store the status packet; this is so we know whether something
    #   is disabled, and know that the search actually occured.
    #   Basically a heartbeat.
    spa = {}
    if fsa != {}:
        # Line length control
        psp = fsa['ProcessStats']['PIDS']

        # These should always be in there, no matter what
        for each in desired:
            try:
                if each == "boottime":
                    spa.update({each: fsa['ProcessStats'][each]*1e3})
                else:
                    spa.update({each: fsa['ProcessStats'][each]})
            except KeyError:
                pass

        # psp == None means we didn't want to search for anything
        if psp is None:
            spa.update({"SearchEnabled": False})
        else:
            spa.update({"SearchEnabled": True})

        # Manually put in the timestamp to display elsewhere
        #   without jumping through dumb hoops
        # But make a string that Grafana can display easily (in ms)
        gts = int(ts.timestamp()*1e3)
        spa.update({"lastchecked": gts})

        # Check to see if we failed to find the process:
        #   Remember that psp is a dict! hasattr() won't work.
        if psp is not None:
            searchstat = 'ProcessNotFound' in psp
            if searchstat is False:
                spa.update({"ProcessNotFound": False})
            else:
                spa.update({"ProcessNotFound": True})

        ptags = tags.copy()
        ptags.update({'type': 'status'})
        # Write a packet that we didn't even try and the status
        #   panel associated with this can be set to 'disabled'
        # Make the packet
        packet = utils.packetizer.makeInfluxPacket(meas=meas,
                                                   ts=ts,
                                                   tags=ptags,
                                                   fields=spa)
        # Store the packet
        if db is not None:
            # Actually commit the packet. singleCommit opens it,
            #   writes the packet, and then optionally closes it.
            db.singleCommit(packet, close=True)

        packets.append(packet)

    # Now for the actual process information, if there is any;
    #   FOR THE LOVE OF THE FLYING SPAGHETTI MONSTER MAKE SURE THESE MATCH
    pdesired = ['age', 'createtime', 'cmdline', 'num_threads',
                'status', 'pid', 'ppid', 'terminal']
    # pdesiredfmt = [float, float, str, int,
    #               str, int, int, str]

    gf = {}
    packets = []
    if fsa != {}:
        # psp == None means we didn't want to search for anything
        if psp is not None:
            # searchstat == False means the process wasn't found at all
            if searchstat is False:
                packet = []
                for npid in psp:
                    # Grab the actual dict values for the numerical PID key
                    pid = psp[npid]
                    # Now fill up a packet with the good stuff
                    for pk in pdesired:
                        try:
                            # Need to flatten some fools first
                            if type(pid[pk]) == list:
                                store = " ".join(pid[pk])
                            else:
                                store = pid[pk]
                            gf.update({pk: store})
                        except KeyError:
                            gf.update({pk: None})

                    # CUSTOM
                    if pid['exe'].startswith('/opt/LOIS'):
                        ptype = "binLOIS"
                        # pstatus = "enabled"
                    # CUSTOM
                    elif pid['exe'] == '/bin/bash':
                        ptype = "scriptLOIS"
                        # pstatus = "enabled"
                    else:
                        ptype = "generic"
                        # pstatus = "enabled"

                    # Need to do this because dicts are mutable
                    ptags = tags.copy()
                    ptags.update({"type": ptype})

                    # Make the packet
                    packet = utils.packetizer.makeInfluxPacket(meas=meas,
                                                               ts=ts,
                                                               tags=ptags,
                                                               fields=gf)
                    # Store the packet
                    if db is not None:
                        # Actually commit the packet. singleCommit opens it,
                        #   writes the packet, and then optionally closes it.
                        db.singleCommit(packet, close=True)

                    # THIS COULD FAIL AND BE WEIRD IF writeToDB ISN'T FIXED
                    packets.append(packet)

    return packets


def actionSpace(eSSH, baseYcmd, iobj, db=None, debug=False):
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
        baseYcmd (:obj:`str`)
            String describing how to properly start Yvette on the target.
            Should include any necessary EXPORT statements before calling
            python to take care of any environment problems.
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

    fcmd = rStringSpace(baseYcmd, iobj.srcdir)
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
        if db is not None:
            # Actually commit the packet. singleCommit opens it,
            #   writes the packet, and then optionally closes it.
            db.singleCommit(packet, close=True)
    return packet


def actionStats(eSSH, baseYcmd, iobj, db=None, debug=False):
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

    fcmd = rStringStats(baseYcmd)
    fs = eSSH.sendCommand(fcmd, debug=debug)
    # Timestamp of when this all (just) occured
    ts = dt.datetime.utcnow()

    # Turn Yvette's JSON answer into an object
    fsa = decodeAnswer(fs, debug=debug)
    if superdebug is True:
        print(fs)
        print(fsa)

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
                gf.update({oach: fsa['MachineLoads'][dbmapLoad[oach]]})
            except KeyError:
                pass

        for pach in dbmapMem.keys():
            try:
                gf.update({pach: fsa['MachineMem'][dbmapMem[pach]]})
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
        if db is not None:
            # Actually commit the packet. singleCommit opens it,
            #   writes the packet, and then optionally closes it.
            db.singleCommit(packet, close=True)
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
    # Sometimes servers just don't give an exit status because they're bastards
    #   so paramiko will just assign -1 to show that. S t u p i d.
    if ans[0] == 0 or ans[0] == -1:
        if ans[1] != '':
            final = json.loads(ans[1])
            if debug is True:
                print(final)
    return final
