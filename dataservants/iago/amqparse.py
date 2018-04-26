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


import time
import datetime as dt
from dateutil import tz
import xmltodict as xmld

import stomp
from stomp.exception import StompException
from stomp.listener import ConnectionListener

from .. import utils


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


class subscriber(ConnectionListener):
    def __init__(self, dbname=None):
        # Adding an extra argument to the subclass
        self.influxdbname = dbname

    # Subclassing stomp.listener.ConnectionListener
    def on_message(self, headers, body):
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

        # Now send the packet to the right place for processing.
        #   These need special parsing because they're just straight text
        if tname == 'joePduResult':
            parserPDU(headers['timestamp'], body, dbname=self.influxdbname)
        if tname == 'lightPathInformation':
            parserLPI(headers['timestamp'], body, dbname=self.influxdbname)
        else:
            # Intended to be the endpoint of the auto-XML influx publisher
            pass


def parserLPI(ts, msg, dbname=None):
    """
    'mirrorCoverMode=Open'
    'instrumentCoverState=OPEN'
    'instrumentCoverStageCoordindate=-19.85'
    'foldMirrorsState=HOME,HOME,HOME,HOME'
    'foldMirrorsStageCoordindates=+0.00,+0.00,+0.00,+0.00'
    """
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


def parserPDU(ts, msg, dbname=None):
    """
    'gwavespdu2.lowell.edu:23 IPC ONLINE!'
    'gwavespdu2.lowell.edu:23 OUTLET 2 ON ( UNIT#0 J2 )NIH-TEMP'
    """
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


def connAMQ(default_host, topics, dbname=None, user=None, passw=None):
    """
    """
    # To identify our subscriptions
    baseid = 8675309

    # TODO:
    #   Put a timer on connection
    #   Make this into a class?

    try:
        print("Connecting to %s" % (default_host))
        conn = stomp.Connection([(default_host, 61613)])

        conn.set_listener('HamSpy', subscriber(dbname=dbname))
        conn.start()
        conn.connect()

        for i, activeTopic in enumerate(topics):
            print("Subscribing to %s" % (activeTopic))
            conn.subscribe("/topic/" + activeTopic, baseid+i)
    except Exception as err:
        print(str(err))
    finally:
        conn.disconnect()
        print("Disconnected from %s" % (default_host))


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
            self.conn = stomp.Connection([(self.host, self.port)])

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
