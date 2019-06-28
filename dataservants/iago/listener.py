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

from __future__ import division, print_function, absolute_import

import xmltodict as xmld
from stomp.listener import ConnectionListener

from ligmos import utils

from .parsetopics import parserPDU, parserLPI, parserLOlogs, \
                         parserFlatPacket, parserSimpleFloat


class DCTConsumer(ConnectionListener):
    def __init__(self, dbconn=None):
        """
        This will really be stuffed into a
        utils.amq.amqHelper class, so all the connections stuff is
        really over there in that class.  This is just to route the
        DCT-specific messages to the right parsers
        """

        # Adding an extra argument to the subclass
        self.dbconn = dbconn

        # Grab all the schemas that are in the ligmos library
        self.schemaDict = utils.amq.schemaDicter()

    def on_message(self, headers, body):
        """
        Basically subclassing stomp.listener.ConnectionListener
        """
        badMsg = False
        tname = headers['destination'].split('/')[-1].strip()
        # Manually turn the bytestring into a string
        try:
            body = body.decode("utf-8")
            badMsg = False
        except UnicodeDecodeError as err:
            print(str(err))
            print("Badness 10000")
            print(body)
            badMsg = True

        if badMsg is False:
            try:
                xml = xmld.parse(body)
                # If we want to have the XML as a string:
                # res = {tname: [headers, dumpPacket(xml)]}
                # If we want to have the XML as an object:
                res = {tname: [headers, xml]}
            except xmld.expat.ExpatError:
                # This means that XML wasn't found, so it's just a string
                #   packet with little/no structure. Attach the sub name
                #   as a tag so someone else can deal with the thing
                res = {tname: [headers, body]}
            except Exception as err:
                # This means that there was some kind of transport error
                #   or it couldn't figure out the encoding for some reason.
                #   Scream into the log but keep moving
                print("="*42)
                print(headers)
                print(body)
                print(str(err))
                print("="*42)
                badMsg = True

        # List of packets that we know have schemas and will work.
        #   Still hardcoding things at the moment.
        vFlats = ['tcs.loisTelemetry',
                  'AOS.AOSPubDataSV.AOSDataPacket',
                  'WRS.WRSPubDataSV.WRSDataPacket',
                  'TCS.TCSSharedVariables.TCSHighLevelStatusSV.TCSTcsStatusSV',
                  'Ryans.DCTWeatherStream']

        # List of packets that we know have a float value and nothing else
        vFloats = ['AOS.AOSSubDataSV.RelativeFocusOffset',
                   'AOS.AOSSubDataSV.AbsoluteFocusOffset',
                   'MTS.MTSPubDataSV.MountTemperature']

        # Now send the packet to the right place for processing.
        #   These need special parsing because they're just straight text
        if badMsg is False:
            try:
                if tname == 'joePduResult':
                    parserPDU(headers, body, db=self.dbconn)
                elif tname == 'lightPathInformation':
                    parserLPI(headers, body, db=self.dbconn)
                elif tname.endswith("loisLog"):
                    parserLOlogs(headers, body, db=self.dbconn)
                elif tname in vFlats:
                    # TODO: Wrap this in a proper try...except
                    #   As of right now, it'll be caught in the "WTF!!!"
                    schema = self.schemaDict[tname]
                    parserFlatPacket(headers, body,
                                     schema=schema, db=self.dbconn)
                elif tname in vFloats:
                    parserSimpleFloat(headers, body, db=self.dbconn)
                else:
                    # Intended to be the endpoint of the auto-XML publisher
                    #   so I can catch most of them rather than explicitly
                    #   check in the if/elif block above
                    print("Orphan topic: %s" % (tname))
                    print(headers)
                    print(body)
                    print(res)
            except Exception as err:
                # This is a catch-all to help find parsing errors that need
                #   to be fixed since they're not caught in a parser* func.
                print("="*11)
                print("WTF!!!")
                print(str(err))
                print(headers)
                print(body)
                print("="*11)


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
