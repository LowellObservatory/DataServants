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

import urllib
from stomp.listener import ConnectionListener

from ligmos.utils import xmlschemas as myxml
from ligmos.utils.messageParsers import parserFlatPacket, parserSimple


class MesaConsumer(ConnectionListener):
    def __init__(self, dbconn=None):
        """
        This will really be stuffed into a
        utils.amq.amqHelper class, so all the connections stuff is
        really over there in that class.  This is just to route the
        Mesa-specific messages to the right parsers
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
        vFlats = ['lig.mesa.NPOIWeatherStation',
                  'LOUI.nasa42.loisTelemetry']

        # List of topics that we know have a float value and nothing else
        vFloats = []

        # List of topics that are just words/strings
        vStrings = []

        # List of topics that are bools (strings saying true/false)
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
                if tname in vFlats:
                    schema = self.schemaDict[tname]
                    print("Schema before call:")
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
            except urllib.error.URLError as err:
                # This actually implies that the message wasn't a valid XML
                #   message and couldn't actually be validated.  I think it's
                #   really a quirk of the xmlschema library but I'm not sure
                print(err)
            except Exception as err:
                # Mostly this catches instances where the topic name doesn't
                #   have a schema, but it catches all oopsies really
                print("="*11)
                print("WTF!!!")
                print(str(err))
                print(headers)
                print(body)
                print("="*11)
