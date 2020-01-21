# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 2 Jan 2020
#
#  @author: rhamilton

"""
"""

from __future__ import division, print_function, absolute_import

from snimpy.mib import SMIException
from snimpy.snmp import SNMPNoSuchName
import snimpy.basictypes as snimpyTypes
from snimpy.manager import load, Manager


def convertDatatypes(vDict):
    """
    """
    if vDict != {}:
        for key in vDict:
            oval = vDict[key]
            if isinstance(oval, snimpyTypes.Enum):
                oval = str(oval)
            elif isinstance(oval, snimpyTypes.String):
                oval = str(oval)
            elif isinstance(oval, snimpyTypes.Integer):
                oval = int(oval)
            else:
                # Additional datatypes needed TBD
                pass

            vDict[key] = oval

    return vDict


def setupSNMPTarget(snmpTarg, loadMIBs=True):
    """
    """
    # Make sure we have a return value for now
    mibOrder = []
    if snmpTarg.devicetype.lower() == "ubnt-airos":
        mibOrder = ["UBNT-MIB.txt", "UBNT-AirMAX-MIB.txt"]
        # Now prepend our basepath to those MIBs
        mibOrder = ["%s/%s" % (snmpTarg.miblocation, mib) for mib in mibOrder]
    elif snmpTarg.devicetype.lower() == "ubnt-unifi":
        mibOrder = ["UBNT-MIB.txt", "UBNT-UniFi-MIB.txt"]
        # Now prepend our basepath to those MIBs
        mibOrder = ["%s/%s" % (snmpTarg.miblocation, mib) for mib in mibOrder]
    elif snmpTarg.devicetype.lower() == "apc-ups":
        pass
    else:
        print("Unknown device: %s" % (snmpTarg.devicetype.lower()))

    if loadMIBs is True:
        print("Loading MIBs:")
        print(mibOrder)
        for mib in mibOrder:
            try:
                load(mib)
            except SMIException as smierr:
                print("ERROR: %s" % (str(smierr)))

    try:
        # Note: the SNMP version must be an integer for snimpy to interpret it
        snmpManager = Manager(host=snmpTarg.host,
                              community=snmpTarg.snmpcommunity,
                              version=int(snmpTarg.snmpversion),
                              timeout=3, retries=3)
    except:
        # TODO: Figure out the correct exception to catch here, if any
        snmpManager = None

    return snmpManager


def grabEndpoints(snmpManager, snmpTarget):
    """
    """
    rdict = {}
    for point in snmpTarget.snmpendpoints:
        print("Searching for %s" % (point))
        try:
            mpoint = getattr(snmpManager, point)
            # Check to see if we just got our desired answer or if we have
            #   to dig inside of the results more
            if isinstance(mpoint, snimpyTypes.OctetString):
                rdict.update({point: mpoint.decode("UTF-8")})
            else:
                for oid, value in mpoint.iteritems():
                    print(point, int(oid), value)
                    spoint = "%s.%d" % (point, int(oid))
                    rdict.update({spoint: value})
        except (AttributeError, SNMPNoSuchName):
            print("%s not found!" % (point))

    return rdict
