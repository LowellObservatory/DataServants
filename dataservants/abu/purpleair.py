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

import pytz

import xmltodict as xmld


def purplePreparer(data, querytimeDT,
                   serverTZ="US/Arizona", devType="PurpleAir_PA-II"):
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
            rjson.update({"queryTS": querytimeDT})

            # Check for weird values that can happen as the sensor
            #   is booting up, and ditch them
            for each in rjson:
                if rjson[each] == 'nan':
                    print("Warning: Removing 'nan' key %s!" % (each))
                    rjson.pop(each)

            # If the sensor just booted, the timestamp will be in the
            #   1970 (Unix 0) epoch so if that's the case, replace it
            #   with the query timestamp and pass it along!  Put it in the
            #   "usual" place that the Iago-style parsers can grab it,
            #   e.g. influx_ts prefixed stamp.
            timestampStr = rjson.pop("DateTime")
            timestampDT = dt.datetime.strptime(timestampStr,
                                               "%Y/%m/%dT%H:%M:%Sz")

            # Add in the timezone by hand to make sure it's clear it's UTC
            #   coming out of the PurpleAir JSON DateTime timestamp.
            # This is unlikely to change unless PurpleAir changes it in the
            #   firmware but that's very unlikely and would be very dumb.
            timestampDT = timestampDT.replace(tzinfo=pytz.UTC)

            # Localize to our SERVER'S timezone - check your own setup!
            #   It's likely to be either UTC, or your server's actual local
            #   timezone.  It depends on who set it up, and who set up influx
            serverTZ = pytz.timezone(serverTZ)
            timestampDT = timestampDT.astimezone(serverTZ)

            # Re-store the original timestamp, now with it's TZinfo too
            rjson['odataTS'] = timestampDT

            # Now do a sanity check; is timestampDT in the default epoch?
            #   If so, just use the system time instead because that implies
            #   that the sensor rebooted, or it lost it's internet connection
            #   so the NTP check didn't work
            if timestampDT.year == 1970:
                print("Warning: Replacing PurpleAir timestamp with my own!")
                print("PA_TS:", timestampDT)
                print("My_TS:", querytimeDT)
                timestampDT = querytimeDT

            # We use _ms here because if we replace the timestamp ourselves
            #   above, we will actually have ms resolution and it might be
            #   nice to just keep that for the future.

            rjson['influx_ts_ms'] = round(timestampDT.timestamp()*1e3)
            print("Data timestamp:", timestampDT)

            # Since it's nice and flat and not too bad JSON already, turn it
            #   into XML to send it to the broker
            paxml = xmld.unparse({"PurpleAir_PA-II": rjson}, pretty=True)
        except Exception as err:
            print("Well shit")
            print(str(err))

    return paxml
