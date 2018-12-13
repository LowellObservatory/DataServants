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

from dataservants import iago


def testSchema(xmlfile, location):
    """
    """
    hed = {'destination': location}
    with open(xmlfile, 'r') as f:
        msg = f.read()

    iago.amqparse.parserFlatPacket(hed, msg, db=None)


def main():
    xmlfile = '../ligmos/ligmos/schemas/xmlsamples/TCS.TCSSharedVariables.TCSHighLevelStatusSV.TCSTcsStatusSV.xml'
    testSchema(xmlfile,
               'TCS.TCSSharedVariables.TCSHighLevelStatusSV.TCSTcsStatusSV')


if __name__ == "__main__":
    main()
