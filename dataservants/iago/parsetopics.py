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

import os
import collections
import datetime as dt

import xmlschema as xmls

from ligmos import utils


def flatten(d, parent_key='', sep='_'):
    """
    Thankfully StackOverflow exists because I'm too tired to write out this
    logic myself and now I can just use this:
    https://stackoverflow.com/a/6027615
    With thanks to:
    https://stackoverflow.com/users/1897/imran
    https://stackoverflow.com/users/1645874/mythsmith
    """
    items = []
    for k, v in d.items():
        new_key = parent_key + sep + k if parent_key else k
        if isinstance(v, collections.MutableMapping):
            items.extend(flatten(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def parserFlatPacket(hed, msg, schema=None, db=None, debug=False):
    """
    """
    # print(msg)
    # This is really the topic name, so we'll make that the measurement name
    #   for the sake of clarity. It NEEDS to be a list until I fix packetizer!
    meas = [os.path.basename(hed['destination'])]

    # Bail if there's a schema not found; needs expansion here
    if schema is None:
        print("No schema found for topic %s!" % (meas[0]))
        return None

    # In this house, we only store valid packets!
    good = schema.is_valid(msg)

    # A DIRTY DIRTY HACK
    try:
        xmlp = schema.to_dict(msg, decimal_type=float, validation='lax')
        # print(xmlp)
        good = True
    except xmls.XMLSchemaValidationError:
        good = False

    if good is True:
        if debug is True:
            print("Packet good!")
        try:
            xmlp = schema.to_dict(msg, decimal_type=float, validation='lax')
            # I HATE THIS
            if isinstance(xmlp, tuple):
                xmlp = xmlp[0]

            # Back to normal.
            keys = xmlp.keys()

            fields = {}
            # Store each key:value pairing
            for each in keys:
                val = xmlp[each]

                # TESTING
                if isinstance(val, dict):
                    flatVals = flatten(val, parent_key=each)
                    fields.update(flatVals)
                else:
                    fields.update({each: val})

            if fields is not None:
                # Note: passing ts=None lets python Influx do the timestamp
                packet = utils.packetizer.makeInfluxPacket(meas=meas,
                                                           ts=None,
                                                           tags=None,
                                                           fields=fields)

                # print(packet)

                # Actually commit the packet. singleCommit opens it,
                #   writes the packet, and then optionally closes it.
                if db is not None:
                    db.singleCommit(packet, table=db.tablename,
                                    close=True)
        except xmls.XMLSchemaDecodeError as err:
            print(err.message.strip())
            print(err.reason.strip())

        # Added for itteratively testing parsed packets outside of the
        #   usual operational mode (like in toymodels/PacketSchemer)
        if debug is True:
            print(fields)
    else:
        if debug is True:
            print("Packet was bad!?")


def parserLOlogs(hed, msg, db=None, badFWHM=100.):
    """
    '22:26:55 Level_4:CCD Temp:-110.06 18.54 Setpoints:-109.95 0.00 '
    '22:26:55 Level_4:Telescope threads have been reactivated'
    """
    # ts = hed['timestamp']
    topic = os.path.basename(hed['destination'])

    # print(ts, msg)
    # Some time shenanigans; the LOIS log doesn't include date but
    #   we can assume it's referencing UT time on the same day.
    #   I suppose that there could be some ambiguity right at UT midnight
    #   ... but oh well.
    now = dt.datetime.utcnow()
    ltime = msg[0:8].split(":")
    # Bail early since this indicates it's not really a log line but
    #   some other type of message (like a LOIS startup or something)
    if len(ltime) != 3:
        print("Unknown log line!")
        print(msg)
        return

    now = now.replace(hour=int(ltime[0]), minute=int(ltime[1]),
                      second=int(ltime[2]), microsecond=0)

    # lts = now.strftime("%Y-%m-%dT%H:%M:%S.%f")
    # Get just the log level
    loglevel = msg.split(" ")[1].split(":")[0]
    # Now get the message, putting back together anything split by ":"
    #   this is so we can operate fully on the full message string
    logmsg = " ".join(msg.split(":")[3:]).strip()

    # print("%s from %s:" % (lts, topic))

    # Set the stage for our eventual influxdb packet
    meas = ['InstrumentTelemetry']
    tags = {'name': topic.split(".")[1]}

    if loglevel in ("Level_5", "Level_4"):
        fields = None
        if logmsg.startswith("CCD sensor adus"):
            # print("Parsing: %s" % (logmsg))
            # CCD sensor adus temp1 2248 temp2 3329 set1 2249 heat1 2016'
            adutemp1 = int(logmsg.split(" ")[4])
            adutemp2 = int(logmsg.split(" ")[6])
            aduset1 = int(logmsg.split(" ")[8])
            aduheat1 = int(logmsg.split(" ")[10])

            fields = {"aduT1": adutemp1}
            fields.update({"aduT2": adutemp2})
            fields.update({"aduT2": adutemp2})
            fields.update({"aduS1": aduset1})
            fields.update({"aduH1": aduheat1})

            # print(adutemp1, adutemp2, aduset1, aduheat1)
        elif logmsg.startswith("CCD Heater"):
            # NOTE! This one will have had a ":" removed by the
            #   logmsg creation line above, so you can just split normally
            # print("Parsing: %s" % (logmsg))
            # CCD Heater Values:1.21 0.00
            heat1 = float(logmsg.split(" ")[3])
            heat2 = float(logmsg.split(" ")[4])

            fields = {"H1": heat1}
            fields.update({"H2": heat2})

            # print(heat1, heat2)
        elif logmsg.startswith("CCD Temp"):
            # Same as "CCD Heater" in that ":" have been removed by this point
            # print("Parsing: %s" % (logmsg))
            # CCD Temp -110.06 18.54 Setpoints -109.95 0.00 '
            temp1 = float(logmsg.split(" ")[2])
            temp2 = float(logmsg.split(" ")[3])
            set1 = float(logmsg.split(" ")[5])
            set2 = float(logmsg.split(" ")[6])

            fields = {"T1": temp1}
            fields.update({"T2": temp2})
            fields.update({"S1": set1})
            fields.update({"S2": set2})
            fields.update({"T1S1delta": temp1-set1})

            # print(temp1, temp2, set1, set2)
        else:
            fields = None
            # print(loglevel, logmsg)
    elif loglevel == "Level_2":
        fields = None
        if logmsg.startswith("SendAnalysis"):
            apts = logmsg.split()
            if apts[3].startswith("PHOT"):
                fnum, subfno = apts[3].split("(")[1].split(")")[0].split(",")
                centx = float(apts[4])
                centy = float(apts[5])
                fwhm = float(apts[6])
                instmag = float(apts[7])
                instmagerr = float(apts[8])
                skymean = float(apts[9])

                tags.update({"frame": fnum})
                tags.update({"subframenum": subfno})

                fields = {"centx": centx}
                fields.update({"centy": centy})
                fields.update({"fwhm": fwhm})
                fields.update({"instmag": instmag})
                fields.update({"instmagerr": instmagerr})
                fields.update({"skymean": skymean})

                # Final check for goodness.
                #   NOTE: The badFWHM value is hardcoded into LOIS when the
                #         centroid or profile fit fails. So we'll skip those.
                if fwhm == badFWHM:
                    # Nuke the entire site from orbit...
                    fields = None
                    tags = None
    else:
        # Need this otherwise we'll get an exception error for all
        #   unparsed log lines! fields won't be defined right below here
        #   and it'll trigger a NameError for 'fields'
        fields = None

    # Make the InfluxDB packet and store it, skipping if fields is None
    if fields is not None:
        # Note: passing ts=None lets python Influx do the timestamp for you
        packet = utils.packetizer.makeInfluxPacket(meas=meas,
                                                   ts=None,
                                                   tags=tags,
                                                   fields=fields)

        # print(packet)

        # Actually commit the packet. singleCommit opens it,
        #   writes the packet, and then optionally closes it.
        if db is not None:
            db.singleCommit(packet, table=db.tablename, close=True)


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


def parserPDU(_, msg, db=None):
    """
    'gwavespdu2.lowell.edu:23 IPC ONLINE!'
    'gwavespdu2.lowell.edu:23 OUTLET 2 ON ( UNIT#0 J2 )NIH-TEMP'
    """
    # ts = hed['timestamp']

    # Cut the hostname down to something more managable
    hostname = msg.split(" ")[0]
    host = hostname.split(":")[0].split(".")[0]

    message = msg.split(" ")[1:]
    if message[0] == "IPC":
        # I don't give two shits about the IPC status messages.
        #   If I'm getting messages of course the IPC is online.
        pass
    elif message[0] == "OUTLET":
        # Ok, now we're talking. Snag stuff out of here.
        outnumb = message[1]
        # Turn the status in to a simple binary (on = 1, off = 0)
        if message[2] == "ON":
            outstat = 1
        else:
            outstat = 0
        # This is the shorthand label/tag at the very end
        label = message[-1].strip("(").strip(")")

        # Make the InfluxDB style packet
        meas = ["PDUStates"]
        # The "tag" is the pdu's hostname since there are multiple
        tag = {"Name": host, "OutletNumber": int(outnumb),
               "Label": label}

        fields = {"State": outstat}
        fields.update({"Label": label})

        # Make and store the influx packet
        # Note: passing ts=None lets python Influx do the timestamp for you
        packet = utils.packetizer.makeInfluxPacket(meas=meas,
                                                   ts=None,
                                                   tags=tag,
                                                   fields=fields)

        # print(packet)

        # Actually commit the packet. singleCommit opens it,
        #   writes the packet, and then optionally closes it.
        if db is not None:
            db.singleCommit(packet, table=db.tablename, close=True)


def parserSimpleFloat(hed, msg, db=None):
    """
    """
    # print("Parsing a simple float message: %s" % msg)
    topic = os.path.basename(hed['destination'])
    try:
        val = float(msg)
    except ValueError as err:
        print(str(err))
        val = -9999.

    # Make the InfluxDB style packet
    meas = [topic]
    tag = {}

    fields = {"value": val}

    # Make and store the influx packet
    # Note: passing ts=None lets python Influx do the timestamp for you
    packet = utils.packetizer.makeInfluxPacket(meas=meas,
                                               ts=None,
                                               tags=tag,
                                               fields=fields)
    # print(packet)

    # Actually commit the packet. singleCommit opens it,
    #   writes the packet, and then optionally closes it.
    if db is not None:
        db.singleCommit(packet, table=db.tablename, close=True)
