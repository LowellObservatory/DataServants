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

from .parser_OMSPDU import parserPDU, parserStageResult


def createOMSPDUConsumer(dbconn=None):
    """
    """
    # Topics that can be parsed directly via XML schema
    tXML = ['joeStage']

    # Topics that are just bare floats
    tFloat = None

    # Topics that are just words/strings
    tStr = None

    # Topics that are just bools
    tBool = None

    # A *dict* of special topics and their custom parser/consumer.
    #   NOTE: the special functions must all take the following arguments:
    #       headers, body, db=None, schema=None
    #   This is to ensure compatibility with the consumer provided inputs!
    tSpecial = {"joePduResult": parserPDU,
                "joeStageResult": parserStageResult}

    # Create our subclassed consumer with the above routes
    consumer = amqL.LIGBaseConsumer(dbconn=dbconn, tSpecial=tSpecial,
                                    tXML=tXML, tFloat=tFloat,
                                    tStr=tStr, tBool=tBool)

    return consumer


class OMSPDUConsumer(ConnectionListener):
    def __init__(self, dbconn=None):
        """
        This is to route the OMS card specific messages to the right parsers.
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

        # List of packets that we know have schemas and will work.
        #   Still hardcoding things at the moment.
        vFlats = ['joeStage']

        # List of packets that we know have a float value and nothing else
        vFloats = []

        # List of packets that are just words/strings
        vStrings = []

        # List of packets that are bools (strings saying true/false)
        vBools = []

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
        if badMsg is False:
            try:
                if tname == 'joePduResult':
                    parserPDU(headers, body, db=self.dbconn)
                elif tname == 'joeStageResult':
                    parserStageResult(headers, body, db=self.dbconn)
                elif tname in vFlats:
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
