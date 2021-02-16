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
import distutils.util as dut

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
    debug = True
    # This is really the topic name, so we'll make that the measurement name
    #   for the sake of clarity. It NEEDS to be a list until I fix packetizer!
    meas = [os.path.basename(hed['destination'])]

    # Bail if there's a schema not found; needs expansion here
    if schema is None:
        print("FATAL ERROR: No schema found for topic %s!" % (meas[0]))
        return None

    # In this house, we only store valid packets!
    if isinstance(schema, dict):
        # For now, just be super lazy and try all the versions defined
        #   and see which one sticks. Warning: it might be none of them!
        best = None
        for verKey in schema:
            testSchema = schema[verKey]
            print("Testing schema:")
            print(testSchema.url)
            good = testSchema.is_valid(msg)
            if good is True:
                # Override the schema variable with the one that worked
                best = verKey
                print("Found working schema %s" % (verKey))
                break
        if best is not None:
            schema = schema[best]
        else:
            print("Failed to find a working schema :(")
            good = False
            schema = None
    else:
        print("Schema was not a dict, so no other versions to check.")
        print(type(schema))
        good = schema.is_valid(msg)

    # A DIRTY DIRTY HACK
    if schema is not None:
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
            print("Trying to_dict")
            xmlp = schema.to_dict(msg, decimal_type=float, validation='lax')
            # I HATE THIS
            if isinstance(xmlp, tuple):
                xmlp = xmlp[0]

            # Back to normal.
            keys = xmlp.keys()

            fields = {}
            # Store each key:value pairing
            print("Storing keys")
            print(keys)
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
                print("Making packet")
                packet = utils.packetizer.makeInfluxPacket(meas=meas,
                                                           ts=None,
                                                           tags=None,
                                                           fields=fields)

                print("Packet done")
                print(packet)

                # Actually commit the packet. singleCommit opens it,
                #   writes the packet, and then optionally closes it.
                if db is not None:
                    print("Sending packet")
                    db.singleCommit(packet, table=db.tablename,
                                    close=True)
                    print("Sent!")
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
            print(hed)
            print(msg)


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

    if loglevel == "Level_2":
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

        # Actually commit the packet. singleCommit opens it,
        #   writes the packet, and then optionally closes it.
        if db is not None:
            db.singleCommit(packet, table=db.tablename, close=True)


def parserStageResult(hed, msg, db=None):
    """
    Since the OMS query/status command is sent at
       AA; RP; RQC; RI;

    Unfortunately, THE ORDER MATTERS since the first reply will come
    with an ACK character (0x06) and and I'm assuming that it's RP.

    Also deals with OMS motion messages, a la
    %000 00000004

    Also deals with detent replies (A*; BX;)
    7e

    Results are *tagged* per axis to keep resulting queries simpler.
    """
    # ts = hed['timestamp']

    cardMessage = msg.split(" ")
    cardOrigin = cardMessage[0].split(":")
    cardIP = cardOrigin[0]
    cardPort = cardOrigin[1]
    omsMsg = cardMessage[1]
    axisLabels = ["AX", "AY", "AZ", "AT", "AU"]

    meas = ["OMSCards"]
    # print("OMS message from %s:%s" % (cardIP, cardPort))
    # print("Message: %s" % (omsMsg))

    # This will hold all of our packets to be sent off to the database
    packets = []
    if omsMsg.startswith('\x06'):
        # This is the ACK from the OMS card, so it's the reply to
        #   RP (report position) OR a user I/O check (BX).
        #
        # The ACK char will be the first character in either case,
        #   and occasionally there's a double ACK; strip all of them out
        vals = omsMsg[1:].strip("\x06").split(',')

        if len(vals) != len(axisLabels):
            if len(vals[0]) == 2:
                fields = {"rawValue": vals[0]}

                # The BX command reads all the user I/O for the car and
                #   returns the bits, so it's for all axes
                tags = {"cardIP": cardIP, "type": "detent", "axis": "AA"}

                packet = utils.packetizer.makeInfluxPacket(meas=meas,
                                                           ts=None,
                                                           tags=tags,
                                                           fields=fields)

                packets += packet
                # print(fields)
        else:
            for i, each in enumerate(vals):
                if each == '':
                    # Alternative: fill with -99999 and still commit?
                    each = None
                else:
                    each = int(each)

                    fields = {"value": each}
                    tags = {"cardIP": cardIP,
                            "type": "position", "axis": axisLabels[i]}
                    packet = utils.packetizer.makeInfluxPacket(meas=meas,
                                                               ts=None,
                                                               tags=tags,
                                                               fields=fields)

                    packets += packet
    elif omsMsg.startswith('%000'):
        # This is a motion status message.  Basically just a switch statement
        #   First part is just a flag, so ignore it.
        # NOTE: I'm treating these as discrete flags, which I think they are?
        #   It could be that they're just the bits, and this could be
        #   made smarter to just do the bit manipulation directly which
        #   would be easier (but look more confusing).
        #
        # Re-get the flags that were split previously
        omsFlag = cardMessage[2]
        if omsFlag == '00000001':
            axis = "AX"
            flagMsg = "Complete"
        elif omsFlag == '00000002':
            axis = "AY"
            flagMsg = "Complete"
        elif omsFlag == '00000004':
            axis = "AZ"
            flagMsg = "Complete"
        elif omsFlag == '00000008':
            axis = "AT"
            flagMsg = "Complete"
        elif omsFlag == '00000010':
            axis = "AU"
            flagMsg = "Complete"

        elif omsFlag == '00000100':
            axis = "AX"
            flagMsg = "AtLimit"
        elif omsFlag == '00000200':
            axis = "AY"
            flagMsg = "AtLimit"
        elif omsFlag == '00000400':
            axis = "AZ"
            flagMsg = "AtLimit"
        elif omsFlag == '00000800':
            axis = "AT"
            flagMsg = "AtLimit"
        elif omsFlag == '00001000':
            axis = "AU"
            flagMsg = "AtLimit"

        elif omsFlag == '00010000':
            axis = "AX"
            flagMsg = "EncoderSlip"
        elif omsFlag == '00020000':
            axis = "AY"
            flagMsg = "EncoderSlip"
        elif omsFlag == '00040000':
            axis = "AZ"
            flagMsg = "EncoderSlip"
        elif omsFlag == '00080000':
            axis = "AT"
            flagMsg = "EncoderSlip"
        elif omsFlag == '00100000':
            axis = "AU"
            flagMsg = "EncoderSlip"

        elif omsFlag == '01000000':
            axis = "AA"
            flagMsg = "CommandError"

        tags = {"cardIP": cardIP, "type": "motionupdate", "axis": axis}
        fields = {"flagType": flagMsg}

        packet = utils.packetizer.makeInfluxPacket(meas=meas,
                                                   ts=None,
                                                   tags=tags,
                                                   fields=fields)

        packets += packet
    else:
        # If there was no ACK, it's going to be a reply to either
        #   RP (report encoder positon)
        #   RQC (report axis command queue)
        #   RI (report axes status)
        # Of those, RI will be text characters and not numbers so take
        #   care of that one first, but *all* of them will have 5 comma
        #   delimited fields (AX, AY, AZ, AT, AU)
        axesValues = omsMsg.split(",")
        if axesValues[0].isalpha():
            # This means it's the RI reply; for each axis, there will be
            #   1st character:
            #     P Moving in positive direction
            #     M Moving in negative direction
            #   2nd character:
            #     D Done (ID, II or IN command has been executed)
            #     N No ID executed yet
            #   3rd character:
            #     L Axis in overtravel. Char 4 tells which direction.
            #        Set to N when limit switch is not active.
            #     N Not in overtravel in this direction
            #   4th character:
            #     H Home switch active. Set to N when home switch not active.
            #     N Home switch not active
            for i, each in enumerate(axesValues):
                axis = axisLabels[i]
                if len(each) == 4:
                    if each[0].lower() == "p":
                        direction = 'Positive'
                    else:
                        direction = 'Negative'
                    if each[1].lower() == "d":
                        doneness = 'Done'
                    else:
                        doneness = 'NotDoneOrNotUsed'
                    if each[2].lower() == "l":
                        overtravel = 'AxisOvertravel'
                    else:
                        overtravel = 'NotOvertravelOrNotUsed'
                    if each[3].lower() == "h":
                        homestate = 'Home'
                    else:
                        homestate = 'NotHomeOrNotUsed'

                    fields = {"TravelDirection": direction,
                              "CommandDone": doneness,
                              "AxisOvertravel": overtravel,
                              "HomeSwitchState": homestate}

                    tags = {"cardIP": cardIP, "type": "states", "axis": axis}
                    packet = utils.packetizer.makeInfluxPacket(meas=meas,
                                                               ts=None,
                                                               tags=tags,
                                                               fields=fields)
                    packets += packet
        else:
            # This means it's either the RE OR RQC reply.  DeVeny and the RC
            #   probes issue both of them, so I cheat a little bit.
            #
            # RCQ always responds for each axis because it's reporting
            #   the command queue on the OMS card, but RE only reports
            #   for actually connected motors.  So if there are any None's,
            #   it's an RE reply.  Flying Spaghetti monster help us if
            #   we actually connect all axes to real things!!!
            vals = omsMsg.strip().split(',')
            isrcq = True

            # I can't figure out how to do this in one single step, so we
            #   will just scan through twice to see what we most likely got
            converted = []
            for i, each in enumerate(vals):
                try:
                    val = int(each)
                except TypeError:
                    # Implies each was None
                    val = None
                except ValueError:
                    # Implies each was ''; see the note above
                    val = None
                    isrcq = False

                # Store the values for our final loop through
                converted.append(val)

            # Making the decision here means that we can't flip mid-processing
            if isrcq is False:
                metric = "encoder"
            else:
                metric = "commandqueue"

            for i, each in enumerate(converted):
                axis = axisLabels[i]
                if each is not None:
                    fields = {"value": each}
                    tags = {"cardIP": cardIP, "type": metric, "axis": axis}

                    packet = utils.packetizer.makeInfluxPacket(meas=meas,
                                                               ts=None,
                                                               tags=tags,
                                                               fields=fields)
                    packets += packet

        print("")
        print(msg.strip())
        print(packets)

        # Actually commit the packet. singleCommit opens it,
        #   writes the packet, and then optionally closes it.
        # if db is not None:
        #     db.singleCommit(packet, table=db.tablename, close=True)


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

        # Actually commit the packet. singleCommit opens it,
        #   writes the packet, and then optionally closes it.
        if db is not None:
            db.singleCommit(packet, table=db.tablename, close=True)


def parserSimple(hed, msg, db=None, datatype='float'):
    """
    """
    # print("Parsing a simple float message: %s" % msg)
    topic = os.path.basename(hed['destination'])
    if datatype.lower() == 'float':
        try:
            val = float(msg)
        except ValueError as err:
            print(str(err))
            val = -9999.
    elif datatype.lower() == 'string':
        val = str(msg)
    elif datatype.lower() == 'bool':
        try:
            val = dut.strtobool(msg)
        except ValueError as err:
            print(str(err))
            val = -9999
    else:
        print("DEFINITELY NOT YET FINISHED")

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

    # Actually commit the packet. singleCommit opens it,
    #   writes the packet, and then optionally closes it.
    if db is not None:
        db.singleCommit(packet, table=db.tablename, close=True)
