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

from ligmos import utils

from .parser_purpleair import parserPurpleAir
from .parser_general import parserFlatPacket, parserSimple


class DevicesConsumer(ConnectionListener):
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
        self.schemaDict = utils.amq.schemaDicter()
        self.schemaList = list(self.schemaDict.keys())
        print(self.schemaDict)

    def on_message(self, headers, body):
        """
        Basically subclassing stomp.listener.ConnectionListener
        """
        badMsg = False
        tname = headers['destination'].split('/')[-1].strip()

        # List of topics that we know have schemas and will work.
        #   Still hardcoding things at the moment.
        vFlats = ['lig.aqi.purpleair.marshill',
                  'lig.aqi.purpleair.ldt.outside',
                  'lig.aqi.purpleair.ldt.dsscabinet',
                  'lig.aqi.purpleair.mesa.outside']

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
        #   These need special parsing because they're formatted strings
        if badMsg is False:
            try:
                if tname in vFlats:
                    try:
                        schema = self.schemaDict[tname]
                    except KeyError:
                        # If we didn't get it right on the first try, fall
                        #   back to a full search of the schemas using the
                        #   current tname as a prefix. Eventually this can
                        #   be optimized at initialization to make a map of
                        #   topic names to schemas/parsers once instead of
                        #   every single time, but that's 2.0 talk.
                        schema = [e for e in self.schemaList if tname.lower().startswith(e)]

                        # Some last minute checks
                        if schema == []:
                            print("WARNING - No schema found!")
                            schema = None
                        else:
                            # If there are multiple results, warn about it
                            #   but then just take the first
                            if len(schema) > 1:
                                print("WARNING - Multiple matching schemas!")
                                print(schema)

                            schemaSelected = schema[0]
                            schema = self.schemaDict[schemaSelected]

                    print("Schema before call:")
                    print(schema)

                    if tname.startswith("lig.aqi.purpleair"):
                        # To make sure nothing gets posted early, I'm
                        #   specifically _not_ handing over the db connection.
                        rP = parserFlatPacket(headers, body,
                                              schema=schema, db=None,
                                              returnParsed=True)

                        # rP == [meas, ts, timeprec, fields]
                        parserPurpleAir(rP[0], rP[1], rP[2], rP[3],
                                        db=self.dbconn)
                    else:
                        parserFlatPacket(headers, body,
                                         schema=schema, db=self.dbconn,
                                         returnParsed=False)
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
