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

from stomp.listener import ConnectionListener

from ligmos.utils import xmlschemas as myxml
from ligmos.utils import amqListeners as amqL
from ligmos.utils.messageParsers import parserFlatPacket, parserSimple

from .parser_LDT import parserLPI


def createLDTConsumer(dbconn=None):
    """
    """
    # Topics that can be parsed directly via XML schema
    tXML = ['AOS.AOSPubDataSV.AOSDataPacket',
            'WRS.WRSPubDataSV.WRSDataPacket',
            'TCS.TCSSharedVariables.TCSHighLevelStatusSV.TCSTcsStatusSV',
            'Ryans.DCTWeatherStream',
            'lig.sitepower.isense']

    # Topics that are just bare floats
    tFloat = ['AOS.AOSSubDataSV.RelativeFocusOffset',
              'AOS.AOSSubDataSV.AbsoluteFocusOffset',
              'MTS.MTSPubDataSV.MountTemperature',
              'DCS.DCSPubDataSV.MountDomeAzimuthDifference']

    # Topics that are just words/strings
    tStr = ['DCS.DSSPubDataSV.PositionStatus']

    # Topics that are just bools
    tBool = ['DCS.DCSPubDataSV.OccultationWarning']

    # A *dict* of special topics and their custom parser/consumer.
    #   NOTE: the special functions must all take the following arguments:
    #       headers, body, db=None, schema=None
    #   This is to ensure compatibility with the consumer provided inputs!
    tSpecial = {"lightPathInformation": parserLPI}

    # Create our subclassed consumer with the above routes
    consumer = amqL.LIGBaseConsumer(dbconn=dbconn, tSpecial=tSpecial,
                                    tXML=tXML, tFloat=tFloat,
                                    tStr=tStr, tBool=tBool)

    return consumer


class LDTConsumer(ConnectionListener):
    def __init__(self, dbconn=None):
        """
        This will really be stuffed into a
        utils.amq.amqHelper class, so all the connections stuff is
        really over there in that class.  This is just to route the
        LDT-specific messages to the right parsers
        """

        # Adding an extra argument to the subclass
        self.dbconn = dbconn

        # Grab all the schemas that are in the ligmos library
        self.schemaDict = myxml.schemaDicter()
        print(self.schemaDict)

    def on_message(self, headers, body):
        """
        Basically subclassing stomp.listener.ConnectionListener
        """
        badMsg = False
        tname = headers['destination'].split('/')[-1].strip()

        # List of topics that we know have schemas and will work.
        #   Still hardcoding things at the moment.
        vFlats = ['AOS.AOSPubDataSV.AOSDataPacket',
                  'WRS.WRSPubDataSV.WRSDataPacket',
                  'TCS.TCSSharedVariables.TCSHighLevelStatusSV.TCSTcsStatusSV',
                  'Ryans.DCTWeatherStream',
                  'lig.sitepower.isense']

        # List of topics that we know have a float value and nothing else
        vFloats = ['AOS.AOSSubDataSV.RelativeFocusOffset',
                   'AOS.AOSSubDataSV.AbsoluteFocusOffset',
                   'MTS.MTSPubDataSV.MountTemperature',
                   'DCS.DCSPubDataSV.MountDomeAzimuthDifference']

        # List of topics that are just words/strings
        vStrings = ['DCS.DSSPubDataSV.PositionStatus']

        # List of topics that are bools (strings saying true/false)
        vBools = ['DCS.DCSPubDataSV.OccultationWarning']

        # Manually turn the bytestring into a string
        try:
            body = body.decode("utf-8")
            badMsg = False
        except UnicodeDecodeError as err:
            print(str(err))
            print("Badness 10000")
            print(body)
            badMsg = True

        # Now send the packet to the right place for processing.
        #   These need special parsing because they're formatted strings
        if badMsg is False:
            try:
                if tname == 'lightPathInformation':
                    parserLPI(headers, body, db=self.dbconn)
                elif tname in vFlats:
                    # TODO: Wrap this in a proper try...except
                    #   As of right now, it'll be caught in the "WTF!!!"
                    schema = self.schemaDict[tname]
                    # print("Schema before call:")
                    print(schema)
                    parserFlatPacket(headers, body,
                                     schema=schema, db=self.dbconn)
                elif tname in vFloats:
                    parserSimple(headers, body, db=self.dbconn,
                                 datatype='float')
                elif tname in vStrings:
                    parserSimple(headers, body, db=self.dbconn,
                                 datatype='string')
                elif tname in vBools:
                    parserSimple(headers, body, db=self.dbconn,
                                 datatype='bool')
                else:
                    # Intended to be the endpoint of the auto-XML publisher
                    #   so I can catch most of them rather than explicitly
                    #   check in the if/elif block above
                    print("Orphan topic: %s" % (tname))
                    print(headers)
                    print(body)
            except Exception as err:
                # Mostly this catches instances where the topic name doesn't
                #   have a schema, but it catches all oopsies really
                print("="*11)
                print("WTF!!!")
                print(str(err))
                print(headers)
                print(body)
                print("="*11)
