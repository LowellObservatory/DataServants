# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 19 April 2021
#
#  @author: rhamilton

"""One line description of module.

Further description.
"""

from __future__ import division, print_function, absolute_import

import json
import datetime as dt

import xmltodict as xmld


def purpleQuery(data, timestamp, devType="PurpleAir_PA-II"):
    """
    """
    # Note that the and is mostly useless, but lets me stub in some
    #   modifications if there is a different one in the future
    paxml = None
    if data != '' and devType.lower() == "purpleair_pa-ii":
        try:
            rjson = json.loads(data)
            # Add in our query timestamp, since it's not 100% possible
            #   to rely on the timestamps in the PA JSON itself.  If the
            #   network gets disconnected, it'll revert to UNIX 0!
            rjson.update({"queryTS": timestamp})

            # Check for weird values that can happen as the sensor
            #   is booting up, and ditch them
            for each in rjson:
                if rjson[each] == 'nan':
                    print("Warning: Removing 'nan' key %s!" % (each))
                    rjson.pop(each)

            # Since it's nice and flat and not too bad JSON already, turn it
            #   into XML to send it to the broker
            paxml = xmld.unparse({"PurpleAir_PA-II": rjson}, pretty=True)
        except Exception as err:
            print("Well shit")
            print(str(err))

    return paxml
