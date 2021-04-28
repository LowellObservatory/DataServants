# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 27 Apr 2021
#
#  @author: rhamilton

"""One line description of module.

Further description.
"""

from __future__ import division, print_function, absolute_import

from datetime import datetime as dt

import pytz
import xmltodict as xmld


def boltwood_clarityii(msg,
                       rootname="BoltwoodCloudSensorII",
                       timezone='US/Arizona'):
    """
    Boltwood ClarityII v3.008 and v3.009 don't actually follow their own
    datasheet, so the output will be 20 fields and not 21; the last one
    is supposed to show the status of the alert/relay but it's never there.

    Date       Time        T V  SKY      AMB   CASE    WIND HUM
    2021-04-27 16:16:23.46 C K  -18.0    8.8   20.8    3.1  53

    DEW  HEA R W Since Now()        c w r d C
    -0.3   0 0 0 00002 044313.67804 2 1 1 3 1
    """
    # Default return value
    npacket = ''

    # File date/time timezone object that we'll need for later
    thisTZ = pytz.timezone(timezone)

    # These are skimmed off the top and processed first
    #   "date", "time", "tempUnits", "windUnits"
    datamap = ["skyTemp", "ambientTemp", "enclosureTemp", "windSpeed",
               "relativeHumidity", "dewpoint", "heaterPercentage",
               "rainFlag", "moistureFlag", "secondsSinceRead",
               "junk", "cloudFlag", "windFlag", "rainFlag", "lightFlag",
               "closureSuggestion"]

    bigFlagMap = {"tempUnit": {"C": "Celsius", "F": "Fahrenheit"},
                  "windUnit": {"K": "km/hr", "M": "mi/hr", "m": "m/s"},
                  "moisture": {0: "dry", 1: "recentMoisture",
                               2: "currentMoisture"},
                  "clouds": {0: "unknown", 1: "clear",
                             2: "cloudy", 3: "verycloudy"},
                  "wind": {0: "unknown", 1: "calm",
                           2: "windy", 3: "verywindy"},
                  "rain": {0: "unknown", 1: "dry",
                           2: "wet", 3: "activelyraining"},
                  "light": {0: "unknown", 1: "dark",
                            2: "light", 3: "verylight"},
                  "closure": {0: "canopen", 1: "close"}}

    # These are almost certianly better handled at the display level but I'll
    #   define them for a rainy day in case I change my mind!
    # bigIndicatorMap = {"skyT": {999: "saturatedHot",
    #                             -999: "saturatedCold",
    #                             -998: "wetSensor"},
    #                    "wind": {-1: "stillHeating",
    #                             -2: "isWet",
    #                             -3: "badA/D",
    #                             -4: "failHeating",
    #                             -5: "lowA/D",
    #                             -6: "highA/D"}}

    allfields = msg.split()

    if len(allfields) != 20:
        print("Wrong number of lines for a ClarityII file!")
        fields = {}
    else:
        datadate = allfields.pop(0)
        datatime = allfields.pop(0)
        dtstr = "%sT%s" % (datadate, datatime)
        dtobj = dt.strptime(dtstr, "%Y-%m-%dT%H:%M:%S.%f")

        # You *need* to do this in this exact way; datetime.replate(tzinfo)
        #   will give weird results like a timezone offset of -07:28 !
        dtobj_aware = thisTZ.localize(dtobj)
        print(dtobj_aware.isoformat())
        dtobj_utc = dtobj_aware.astimezone(pytz.UTC)

        try:
            tempUnits = bigFlagMap['tempUnit'][allfields.pop(0)]
        except KeyError:
            tempUnits = "unknown"

        try:
            windUnits = bigFlagMap['windUnit'][allfields.pop(0)]
        except KeyError:
            windUnits = "unknown"

        # Start to assemble the output dictionary
        fields = {"datetime": dtobj_utc,
                  "tempUnits": tempUnits,
                  "windUnits": windUnits}

        for i, col in enumerate(datamap):
            # Stupid, but it works and is readable.
            oval = allfields[i]
            # This is the big block of dumb logic that translates the flags
            #   to the human-readable values.  Technically I could do this at
            #   the display level, and I still might ditch this and do so
            if col == "rainFlag":
                val = bigFlagMap['rain'][int(oval)]
            elif col == "moistureFlag":
                val = bigFlagMap['moisture'][int(oval)]
            elif col == "cloudFlag":
                val = bigFlagMap['clouds'][int(oval)]
            elif col == "windFlag":
                val = bigFlagMap['wind'][int(oval)]
            elif col == "lightFlag":
                val = bigFlagMap['light'][int(oval)]
            elif col == "secondsSinceRead":
                val = int(oval)
            elif col == "closureSuggestion":
                val = bigFlagMap['closure'][int(oval)]
            else:
                val = float(oval)

            # This was a hack to skip the useless Now() field
            if col != "junk":
                newfield = {col: val}
                fields.update(newfield)
            else:
                print(col, val)

            root = {rootname: fields}
            if fields != {}:
                npacket = xmld.unparse(root, pretty=True)

    return npacket
