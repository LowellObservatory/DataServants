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

from ligmos.utils import amqListeners as amqL

from .parser_purpleair import parserPurpleAir


def MHConsumer(dbconn=None):
    """
    """
    # Topics that can be parsed directly via XML schema
    tXML = ['lig.weather.clark.basestation',
            'lig.weather.clark.outdoorstation',
            'lig.weather.clark.raingauge',
            'lig.weather.clark.windgauge',
            'lig.weather.timo.boltwoodii',
            'lig.weather.timo.aagcloudwatcher']

    # Topics that can be parsed directly via XML schema, but require more work
    # A *dict* of special topics and their custom parser/consumer.
    #   NOTE: the special functions must all take the following arguments:
    #       headers, body, db=None, schema=None
    #   This is to ensure compatibility with the consumer provided inputs!
    tkXMLSpecial = {'lig.aqi.purpleair.marshill': parserPurpleAir}

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
    tSpecial = None

    # Create our subclassed consumer with the above routes
    consumer = amqL.LIGBaseConsumer(dbconn=dbconn,
                                    tSpecial=tSpecial,
                                    tkXMLSpecial=tkXMLSpecial,
                                    tXML=tXML, tFloat=tFloat,
                                    tStr=tStr, tBool=tBool)

    return consumer
