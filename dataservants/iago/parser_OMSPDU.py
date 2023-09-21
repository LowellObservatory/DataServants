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


def parserStageResult(hed, msg, db=None, schema=None):
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

    NOTE: schema=None is just to keep compatibility when using this as
          a bound method elsewhere and generally called. It's not used here.
    """
    # ts = hed['timestamp']

    cardMessage = msg.split(" ")
    cardOrigin = cardMessage[0].split(":")
    cardIP = cardOrigin[0]
    cardPort = cardOrigin[1]
    omsMsg = cardMessage[1]
    axisLabels = ["AX", "AY", "AZ", "AT", "AU"]

    # The unconnected 5th axis of each OMS card is used as a dirty
    #   hack to figure out what the answer to "RP" and "RE" should look like
    # See also: edu.lowell.lig.common.utils.ApplicationConstants.java
    #
    # I hate this but it wasn't my doing!
    RPEnd = ",0"
    REEnd = ",,"

    meas = ["OMSCards"]
    # print("OMS message from %s:%s" % (cardIP, cardPort))
    # print("Message: %s" % (omsMsg))

    # This will hold all of our packets to be sent off to the database
    packets = []

    # The ACK char can occasionally be doubled, so strip them all
    vals = omsMsg.strip("\x06").split(',')

    if omsMsg.startswith('%000'):
        # This is a motion status message.
        # NOTE: I'm treating these as discrete flags, which I think they are?

        # The initial .split(" ") at the get go orphaned the flags so get them
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

        tags = {"cardIP": cardIP,
                "port": cardPort,
                "type": "motionupdate", "axis": axis}
        fields = {"flagType": flagMsg}

        packet = utils.packetizer.makeInfluxPacket(meas=meas,
                                                   ts=None,
                                                   tags=tags,
                                                   fields=fields)

        packets += packet
    elif len(vals) != len(axisLabels):
        # Check to see if this is an OMS user I/O query (detent) like "AZ; BX;"
        #   It'll just be two bytes if so
        if len(vals[0]) == 2:
            fields = {"rawValue": vals[0]}

            # The BX command reads all the user I/O for the car and
            #   returns the bits, so it's for all axes
            tags = {"cardIP": cardIP,
                    "port": cardPort,
                    "type": "detent", "axis": "AA"}

            packet = utils.packetizer.makeInfluxPacket(meas=meas,
                                                       ts=None,
                                                       tags=tags,
                                                       fields=fields)

            packets += packet
            # print(fields)
    else:
        # This means it's either an RP, RE, RQC, or RI type answer
        #   We use the cheat mentioned above about the line ending to choose
        #     RE (report encoder position)
        #     RP (report positon)
        #     RQC (report axis command queue)
        #     RI (report axes status)
        if omsMsg.endswith(RPEnd):
            cmdType = "RP"
            metric = "position"
        elif omsMsg.endswith(REEnd):
            cmdType = "RE"
            metric = "encoder"
        else:
            if vals[0].isalpha():
                # This means the first value looks like 'MNNH'
                cmdType = "RI"
                metric = "states"
            else:
                # This means it's just another number to int() later on
                cmdType = "RQC"
                metric = "commandqueue"

        if cmdType == "RI":
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
            for i, each in enumerate(vals):
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

                    tags = {"cardIP": cardIP,
                            "port": cardPort,
                            "type": metric, "axis": axis}
                    packet = utils.packetizer.makeInfluxPacket(meas=meas,
                                                               ts=None,
                                                               tags=tags,
                                                               fields=fields)
                    packets += packet
        elif cmdType in ["RP", "RE", "RQC"]:
            for i, each in enumerate(vals):
                if each == '':
                    val = None
                else:
                    val = int(each)

                    fields = {"value": val}
                    tags = {"cardIP": cardIP,
                            "port": cardPort,
                            "type": metric,
                            "axis": axisLabels[i]}
                    packet = utils.packetizer.makeInfluxPacket(meas=meas,
                                                               ts=None,
                                                               tags=tags,
                                                               fields=fields)

                    packets += packet

        # print(msg.strip())
        print(packets)

    if packets != []:
        # Actually commit the packet. singleCommit opens it,
        #   writes the packet, and then optionally closes it.
        if db is not None:
            db.singleCommit(packets, table=db.tablename, close=True)


def parserPDU(_, msg, db=None, schema=None):
    """
    'gwavespdu2.lowell.edu:23 IPC ONLINE!'
    'gwavespdu2.lowell.edu:23 OUTLET 2 ON ( UNIT#0 J2 )NIH-TEMP'

    NOTE: schema=None is just to keep compatibility when using this as
          a bound method elsewhere and generally called. It's not used here.
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
