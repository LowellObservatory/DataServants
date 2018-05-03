# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 20 Apr 2018
#
#  @author: rhamilton

"""One line description of module.

Further description.
"""

import os
import time
import datetime as dt
from dateutil import tz
import xmltodict as xmld

import stomp
from stomp.exception import StompException
from stomp.listener import ConnectionListener

from .. import utils


class amqHelper():
    def __init__(self, default_host, topics,
                 dbname=None, user=None, passw=None, port=61613,
                 baseid=8675309, connect=True):
        self.host = default_host
        self.port = port
        self.topics = topics
        self.baseid = baseid
        self.dbname = dbname
        self.user = user
        self.password = passw

        if connect is True:
            self.connect(baseid=self.baseid)

    def connect(self, baseid=8675309):
        # TODO:
        #   Put a timer on connection
        try:
            print("Connecting to %s" % (self.host))
            self.conn = stomp.Connection([(self.host, self.port)],
                                         auto_decode=False)

            self.conn.set_listener('HamSpy', subscriber(dbname=self.dbname))
            self.conn.start()
            self.conn.connect()

            for i, activeTopic in enumerate(self.topics):
                print("Subscribing to %s" % (activeTopic))
                self.conn.subscribe("/topic/" + activeTopic, baseid+i)
        except StompException as err:
            self.conn = None
            print(str(err))

    def disconnect(self):
        if self.conn is not None:
            self.conn.disconnect()
            print("Disconnected from %s" % (self.host))


class subscriber(ConnectionListener):
    def __init__(self, dbname=None):
        # Adding an extra argument to the subclass
        self.influxdbname = dbname

    # Subclassing stomp.listener.ConnectionListener
    def on_message(self, headers, body):
        badMsg = False
        tname = headers['destination'].split('/')[-1]
        try:
            xml = xmld.parse(body)
            # If we want to have the XML as a string:
            # res = {tname: [headers, dumpPacket(xml)]}
            # If we want to have the XML as an object:
            res = {tname: [headers, xml]}
        except xmld.expat.ExpatError:
            # This means that XML wasn't found, so it's likely just a string
            #   packet with little/no structure. Attach the subscription name
            #   as a tag so someone else can deal with the thing
            res = {tname: [headers, body]}
        except Exception as err:
            # This means that there was some kind of transport error
            #   or it couldn't figure out the encoding for some reason.
            #   Scream into the log but keep moving
            # NOTE: Might need to set auto_decode=False in the connection...
            print("="*42)
            print(headers)
            print(body)
            print(str(err))
            print("="*42)
            badMsg = True

        # Now send the packet to the right place for processing.
        #   These need special parsing because they're just straight text
        if badMsg is False:
            try:
                if tname == 'joePduResult':
                    parserPDU(headers, body, dbname=self.influxdbname)
                elif tname == 'lightPathInformation':
                    parserLPI(headers, body, dbname=self.influxdbname)
                elif tname.endswith("loisLog"):
                    parserLOlogs(headers, body, dbname=self.influxdbname)
                else:
                    # Intended to be the endpoint of the auto-XML publisher
                    pass
            except Exception as err:
                # This is a catch-all to help find parsing errors that need
                #   to be fixed since they're not caught in a parser* func.
                print("="*11)
                print("WTF!!!")
                print(str(err))
                print(headers)
                print(body)
                print("="*11)


def packetVintage(ts, nowUTC):
    """
    Given an XML packet's timestamp, return how old it is compared to when
    it was queried/grabbed.
    Does some datetime/timezone shenanigans to account for UTC offset of
    the timestamp as reported.
    """
    # Fun with datetime...stupid colon in the UTC offset! Kill it with fire.
    if ":" == ts[-3:-2]:
        ts = ts[:-3]+ts[-2:]
    # Now parse the timestamp normally
    dtts = dt.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S.%f%z")
    dtts_utc = dtts.astimezone(tz.tzutc())
    # Now trim out the tzinfo so we can just subtract. MUST assign again here!
    dtts_utc = dtts_utc.replace(tzinfo=None)
    vintage = ((nowUTC - dtts_utc).total_seconds())
    return vintage


def dumpPacket(pxml):
    """
    Given a packet parsed by xmltodict, unparse it and spit it out to the
    console so you can actually see what's in the thing.

    Assumes that the first element of the parsed XML packet is a descriptive
    name of whatever it actually is.  UPDATE: It definitely isn't.
    """
    # Actually unparse it and then spit it out
    pretty = xmld.unparse(pxml, pretty=True)

    return pretty


def parserLOlogs(hed, msg, dbname=None):
    """
    '22:26:55 Level_4:CCD Temp:-110.06 18.54 Setpoints:-109.95 0.00 '
    '22:26:55 Level_4:Telescope threads have been reactivated'
    """
    ts = hed['timestamp']
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

    lts = now.strftime("%Y-%m-%dT%H:%M:%S.%f")
    # Get just the log level
    loglevel = msg.split(" ")[1].split(":")[0]
    # Now get the message, putting back together anything split by ":"
    #   this is so we can operate fully on the full message string
    logmsg = " ".join(msg.split(":")[3:]).strip()

    # print("%s from %s:" % (lts, topic))

    # Set the stage for our eventual influxdb packet
    meas = ['InstrumentTelemetry']
    tags = {'name': topic.split(".")[1]}

    if loglevel == "Level_5" or loglevel == "Level_4":
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

        # Make the InfluxDB packet and store it, skipping if fields is None
        if fields is not None:
            # Note: passing ts=None lets python Influx do the timestamp for you
            packet = utils.packetizer.makeInfluxPacket(meas=meas,
                                                       ts=None,
                                                       tags=tags,
                                                       fields=fields)

            print(packet)

            # Actually commit the packet
            dbase = utils.database.influxobj(dbname, connect=True)
            # No arguments here means a default of 6 weeks of data held
            dbase.alterRetention()

            dbase.writeToDB(packet)
            dbase.closeDB()
    else:
        pass


def parserLPI(hed, msg, dbname=None):
    """
    'mirrorCoverMode=Open'
    'instrumentCoverState=OPEN'
    'instrumentCoverStageCoordindate=-19.85'
    'foldMirrorsState=HOME,HOME,HOME,HOME'
    'foldMirrorsStageCoordindates=+0.00,+0.00,+0.00,+0.00'
    """
    ts = hed['timestamp']

    key = msg.split("=")[0]
    value = msg.split("=")[1]
    covers, coords = False, False

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
    elif key.lower() == "foldmirrorsdtagecoordindates":
        f1, f2, f3, f4 = value.split(",")
        f1 = float(f1)
        f2 = float(f2)
        f3 = float(f3)
        f4 = float(f4)
        coords = True
    elif key.lower() == "instrumentcoverstagecoordindate":
        i1 = float(value)
        coords = True
    else:
        # If it's not one of these, just cheat and pass
        dbname = None

    if dbname is not None:
        meas = ["LightPath"]
        if covers is True:
            tags = {"Covers": key}
            fields = {"State": value}
        elif coords is True:
            # Figure out which coordinates we're storing
            try:
                # If this exists, if'll just pass by
                i1
                fields = {"CoverCoord": i1}
                tags = {"Coordinates": "InstCover"}
            except NameError:
                fields = {"Mirror1": f1}
                fields.update({"Mirror2": f2})
                fields.update({"Mirror3": f3})
                fields.update({"Mirror4": f4})
                tags = {"Coordinates": "CubeMirrors"}

        # Note: passing ts=None lets python Influx do the timestamp for you.
        packet = utils.packetizer.makeInfluxPacket(meas=meas,
                                                   ts=None,
                                                   tags=tags,
                                                   fields=fields)

        # Actually commit the packet
        dbase = utils.database.influxobj(dbname, connect=True)
        # No arguments here means a default of 6 weeks of data held
        dbase.alterRetention()

        dbase.writeToDB(packet)
        dbase.closeDB()

        print(meas, tags, fields)


def parserPDU(hed, msg, dbname=None):
    """
    'gwavespdu2.lowell.edu:23 IPC ONLINE!'
    'gwavespdu2.lowell.edu:23 OUTLET 2 ON ( UNIT#0 J2 )NIH-TEMP'
    """
    ts = hed['timestamp']

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

        if dbname is not None:
            # Make the InfluxDB style packet
            meas = ["PDUStates"]
            # The "tag" is the pdu's hostname since there are multiple
            tag = {"Name": host, "OutletNumber": int(outnumb)}

            fields = {"State": outstat}
            fields.update({"Label": label})

            # Make and store the influx packet
            # Note: passing ts=None lets python Influx do the timestamp for you
            packet = utils.packetizer.makeInfluxPacket(meas=meas,
                                                       ts=None,
                                                       tags=tag,
                                                       fields=fields)

            print(packet)

            # Actually commit the packet
            dbase = utils.database.influxobj(dbname, connect=True)
            # No arguments here means a default of 6 weeks of data held
            dbase.alterRetention()

            dbase.writeToDB(packet)
            dbase.closeDB()

            print(meas, tag, fields)
