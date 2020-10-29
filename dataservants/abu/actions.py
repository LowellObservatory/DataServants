# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 1 May 2019
#
#  @author: rhamilton

"""One line description of module.

Further description.
"""

from __future__ import division, print_function, absolute_import


import xmltodict as xmld


def amqStats(msg):
    pass


def columbiaTranslator(msg):
    """
    Translate the "XML" file that the Columbia Weather Systems station is
    putting out into something that fits easier into the XML schema/parsing
    way of life.

    I hate this.
    """
    pdict = xmld.parse(msg)

    # There's only ever one root, so just cut to the chase
    pdict = pdict['oriondata']

    stationName = pdict['@station']
    # Since this is eventually going to become XML, we need to define a root
    #   key for the document; make it the stationName for simplicity
    root = {stationName: None}

    # Now loop over each individual measurement in the orig. crap packet
    valdict = {}
    for imeas in pdict['meas']:
        mn = imeas['@name']
        mv = imeas['#text']
        newEntry = {mn: mv}

        valdict.update(newEntry)

    # Add our values to this station
    root[stationName] = valdict

    # Now turn it into an XML string so we can pass it along to the broker
    #   using the magic that is xmld's unparse() method
    npacket = xmld.unparse(root, pretty=True)

    return npacket
