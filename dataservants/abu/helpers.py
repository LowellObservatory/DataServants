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

import xml

import xmltodict as xmld


def xmlParserCatcher(msg, attr_prefix=None):
    """
    Making this a little util function so I don't have to copy this
    exception check into literally every XML parsing function
    """

    pdict = {}
    if attr_prefix is None:
        # This is xmltodict's default so just put it back
        attr_prefix = "@"

    try:
        pdict = xmld.parse(msg, attr_prefix=attr_prefix)
    except xml.parsers.expat.ExpatError as e:
        print("XML Parsing Error!")
        print(str(e))
        print(msg)

    return pdict
