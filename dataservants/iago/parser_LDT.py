# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 28 Jun 2019
#
#  @author: rhamilton

"""One line description of module.

Further description.
"""

from __future__ import division, print_function, absolute_import

from ligmos import utils


def parserLPI(_, msg, db=None):
    """
    'mirrorCoverMode=Open'
    'instrumentCoverState=OPEN'
    'instrumentCoverStageCoordindate=-19.85'
    'foldMirrorsState=HOME,HOME,HOME,HOME'
    'foldMirrorsStageCoordindates=+0.00,+0.00,+0.00,+0.00'
    """
    # ts = hed['timestamp']

    key = msg.split("=")[0]
    value = msg.split("=")[1]
    covers, coords = False, False
    skip = False

    if key.lower() == 'mirrorcovermode' or \
       key.lower() == 'instrumentcoverstate':
        if value.lower() == "open":
            value = 1
        else:
            value = 0

        # Reformat the key to be nicer
        if key.lower() == 'mirrorcovermode':
            key = "MirrorCover"
        else:
            key = "InstrumentCover"

        # Cheaty flag for later
        covers = True
    elif key.lower() == "foldmirrorsstagecoordindates":
        f1, f2, f3, f4 = value.split(",")
        f1 = float(f1)
        f2 = float(f2)
        f3 = float(f3)
        f4 = float(f4)
        coords = True
        # Logic to suss out the active cube port.
        #   I tried to do this all in Grafana but it's too much
        #   of a stupid hassle since I can't really combine metrics.
        # There's 4 fold mirrors, so 5 possible ports
        #   As of 2018 08, mirror 1 is a NIR dichroic so that means
        #   technically two ports are active or available at least.
        inthresh = 100
        # Default port status;
        #   port[0] is the bottom/thru port
        #   ports[1:] are directly mapped to the fold mirrors
        #   To match other terminology:
        #   Ports A, B, C, D == Mirror 1, 2, 3, 4
        port0, port1, port2, port3, port4 = 0, 0, 0, 0, 0
        if f1 > inthresh:
            port0, port1, port2, port3, port4 = 0, 1, 0, 0, 0
        elif f2 > inthresh:
            port0, port1, port2, port3, port4 = 0, 0, 1, 0, 0
        elif f3 > inthresh:
            port0, port1, port2, port3, port4 = 0, 0, 0, 1, 0
        elif f4 > inthresh:
            port0, port1, port2, port3, port4 = 1, 0, 0, 0, 1
        else:
            port0, port1, port2, port3, port4 = 1, 0, 0, 0, 0
    elif key.lower() == "instrumentcoverstagecoordindate":
        i1 = float(value)
        coords = True
    else:
        # If it's not one of these, just cheat and pass
        #   (to skip "foldMirrorsState=..." for example)
        skip = True

    if skip is False:
        meas = ["LightPath"]
        if covers is True:
            tags = {"Covers": key}
            fields = {"State": value}
        elif coords is True:
            # Figure out which coordinates we're storing
            if 'i1' in vars():
                fields = {"CoverCoord": i1}
                tags = {"Coordinates": "InstCover"}
            else:
                fields = {"Mirror1": f1}
                fields.update({"Mirror2": f2})
                fields.update({"Mirror3": f3})
                fields.update({"Mirror4": f4})

                fields.update({"Port0State": port0})
                fields.update({"Port1State": port1})
                fields.update({"Port2State": port2})
                fields.update({"Port3State": port3})
                fields.update({"Port4State": port4})

                tags = {"Coordinates": "CubeMirrors"}

        # Note: passing ts=None lets python Influx do the timestamp for you.
        packet = utils.packetizer.makeInfluxPacket(meas=meas,
                                                   ts=None,
                                                   tags=tags,
                                                   fields=fields)

        # print(packet)

        # Actually commit the packet. singleCommit opens it,
        #   writes the packet, and then optionally closes it.
        if db is not None:
            db.singleCommit(packet, table=db.tablename, close=True)
