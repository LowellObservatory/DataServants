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


def parserFlatPacket(hed, msg, schema=None, db=None, debug=False,
                     timestampKey=None):
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
            # print("Testing schema:")
            # print(testSchema.url)
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
        # print("Schema was not a dict, so no other versions to check.")
        # print(type(schema))
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
            # print("Storing keys")
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
                if timestampKey is not None:
                    # Find a key that starts with the given timestampKey.  In
                    #   pretty much all the cases I control, this will be
                    #   influx_ts_s or influx_ts_ms
                    # It's assumed that it's already in the right format,
                    #   e.g. INTEGER quantity from the epoch; if it's wrong,
                    #   you'll get influxdb errors in the log and nothing will
                    #   actually be posted!
                    fieldKeys = fields.keys()
                    try:
                        if "%s_s" % (timestampKey) in fieldKeys:
                            timeprec = "s"
                        elif if "%s_ms" % (timestampKey) in fieldKeys:
                            timeprec = "ms"
                        elif if "%s_ns" % (timestampKey) in fieldKeys:
                            timeprec = "ns"
                        else:
                            timeprec = 's'
                            ts = None

                        if ts is not None:
                            validTSKey = validTS = "%s_%s" % (timestampKey,
                                                              timeprec)
                            ts = fields.pop(timestampKey)
                    except KeyError:
                        print("Timestamp key %s not found; defaulting to None"
                              % (timestampKey))
                        ts = None
                        timeprec = 's'

                # Note: passing ts=None lets python Influx do the timestamp
                # print("Making packet")
                packet = utils.packetizer.makeInfluxPacket(meas=meas,
                                                           ts=ts,
                                                           tags=None,
                                                           fields=fields)

                # print("Packet done")
                print(packet)

                # Actually commit the packet. singleCommit opens it,
                #   writes the packet, and then optionally closes it.
                if db is not None:
                    print("Sending packet")
                    db.singleCommit(packet, table=db.tablename,
                                    close=True, timeprec=timeprec)
                    # print("Sent!")
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
