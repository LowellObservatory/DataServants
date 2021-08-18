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
