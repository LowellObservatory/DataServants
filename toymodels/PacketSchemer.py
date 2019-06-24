# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 13 Dec 2018
#
#  @author: rhamilton

"""One line description of module.

Further description.
"""

from __future__ import division, print_function, absolute_import

# REMEMBER: Call this FROM the top directory so the import doesn't barf!
import sys
sys.path.append(".")

from ligmos.utils import amq
from dataservants import iago
from dataservants import abu


def testSchema(msg, location):
    """
    """
    hed = {'destination': location}

    schemaObj = amq.checkSchema(location)

    iago.amqparse.parserFlatPacket(hed, msg, db=None,
                                   schema=schemaObj, debug=True)


def main():
    xmlfile = '../ligmos/ligmos/schemas/xmlsamples/dctstation_orig.xml'
    topicname = 'Ryans.DCTWeatherStream'

    # Read in the example packet
    with open(xmlfile, 'r') as f:
        msg = f.read()

    # Perform any reprocessing if necessary
    #   Usually there isn't, unless you're testing a producer/repacking
    betterXML = abu.actions.columbiaTranslator(msg)
    print(betterXML)

    testSchema(betterXML, topicname)


if __name__ == "__main__":
    main()
