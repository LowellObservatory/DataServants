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

from datetime import datetime as dt

import pytz
import xmltodict as xmld

from .helpers import xmlParserCatcher


def prepWU(config, vals, tstamp):
    # See also:
    #
    # https://support.weather.com/s/article/PWS-Upload-Protocol?language=en_US
    #
    # wunderground = 'https://weatherstation.wunderground.com/'
    wunderground = 'https://rtupdate.wunderground.com/'
    wunderground += 'weatherstation/updateweatherstation.php'

    # These are all REQUIRED
    init = {"ID": config.id,
            "PASSWORD": config.key,
            "dateutc": tstamp.strftime("%Y-%m-%d %H:%M:%S"),
            "action": "updateraw",
            "softwaretype": "WeatherPosterMcWeatherPosterFace",
            "realtime": 1,
            "rtfreq": 120.}

    # This is the dict that maps between the WUnderground API fields and the
    #   fields in vals; WUnderground API keys are first.
    # NOTE: This can be expanded to other WX station types with an added
    #   argument here as well as a better/less hardcoded Abu setup!
    allkeys = {"winddir": "mt3SecRollAvgWindDir",
               "windspeedmph": "mt3SecRollAvgWindSpeed",
               "windgustdir": "mt10MinWindGustDir",
               "windgustmph": "mt10MinWindGustSpeed",
               "winddir_avg2m": "mt2MinRollAvgWindDir",
               "windspdmph_avg2m": "mt2MinRollAvgWindSpeed",
               "windgustmph_10m": "mt10MinWindGustSpeed",
               "windgustdir_10m": "mt10MinWindGustDir",
               "humidity": "mtRelHumidity",
               "dewptf": "mtDewPoint",
               "rainin": "mtRainLastHr",
               "dailyrainin": "mtRainToday",
               "tempf": "mtTemp1",
               "baromin": "mtAdjBaromPress"}

    toJSON = {}
    for key in allkeys:
        try:
            toJSON.update({key: float(vals[allkeys[key]])})
        except KeyError:
            print("FAILED TO FIND KEY %s" % (key))

    # The WUnderground data submission point expects everything
    #   to be in the request itself, not the body of the request,
    #   so stuff it all together and give it back to the caller.
    final = {}
    final.update(init)
    final.update(toJSON)

    return wunderground, final


def parseColumbia(msg, returnDict=False):
    """
    Translate the "XML" file that the Columbia Weather Systems station is
    putting out into something that fits easier into the XML schema/parsing
    way of life.

    I hate this.
    """
    pdict = xmlParserCatcher(msg)

    if pdict != {}:
        # There's only ever one root, so just cut to the chase
        pdict = pdict['oriondata']

        stationName = pdict['@station']
        # Since this is eventually going to become XML, we need to define a
        #   root key for the document; make it the stationName for simplicity
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
    else:
        npacket = None
        valdict = {}

    if returnDict is True:
        # We return valdict here because the station name is unimportant
        #   for what this will be used for (e.g. republishing online)
        return npacket, valdict
    else:
        return npacket


def parseMeteobridge(msg,
                     stationName="MHClark", stationType="DavisVantagePro2"):
    """
    Translate the "XML" file that the Meteobridge is putting out into
    something that fits easier into the XML schema/parsing way of life.

    I hate this too.
    """
    pdict = xmlParserCatcher(msg, attr_prefix='')

    if pdict != {}:
        # There's only ever one root, so just cut to the chase
        pdict = pdict['logger']

        # Now loop over each individual measurement in the orig. crap packet
        if stationType.lower() == "davisvantagepro2":
            valueMap = {"THB": "BaseStation",
                        "TH": "OutdoorStation",
                        "RAIN": "RainGauge",
                        "WIND": "WindGauge"}

            allXMLs = {}
            for meas in valueMap:
                valdict = {}
                # Store each section as its own XML packet because each one
                #   has its own timestamp, so this lets us store them in the
                #   database with the right timestamps each time
                baseKey = "%s_%s" % (stationName, valueMap[meas])
                print("baseKey:", baseKey)
                try:
                    vals = pdict[meas]
                except KeyError as err:
                    print(str(err))
                    vals = None

                thesevals = {}
                if vals is not None:
                    for value in vals:
                        if value.lower() == 'date':
                            mv = dt.strptime(vals[value], "%Y%m%d%H%M%S")
                            # And now we do the dumb dance to put the TZ into
                            #   the timestamp, and then convert it to MST which
                            #   is what the server is set up to expect
                            mv = mv.replace(tzinfo=pytz.UTC)
                            mv = mv.astimezone(pytz.timezone("US/Arizona"))

                            thesevals.update({"influx_ts_s":
                                              round(mv.timestamp())})
                            thesevals.update({"timestampdt": mv})
                        elif value.lower() != 'id':
                            # Skip the useless 'id' attribute
                            try:
                                mv = float(vals[value])
                            except ValueError as err:
                                # Just in case there's a string we forgot about
                                print(str(err))
                                mv = None
                            if mv is not None:
                                newEntry = {value: mv}
                                thesevals.update(newEntry)

                valdict.update({baseKey: thesevals})
                # print(valdict)
                npacket = xmld.unparse(valdict, pretty=True)
                # print(npacket)
                allXMLs.update({valueMap[meas].lower(): npacket})
    else:
        allXMLs = {}

    return allXMLs


def parseVirtualWeatherStation(msg,
                               rootname="MHTiMoWeather",
                               timezone='US/Arizona'):
    """
    """
    # Default return value
    npacket = ''

    # File date/time timezone object that we'll need for later
    thisTZ = pytz.timezone(timezone)

    # We don't need/want absolutely everything in here, this is just the
    #   things that are most likely to be cared about/useful.  These are
    #   zero indexed so I can just use them directly to store stuff
    storageMap = {7: "WindSpeed", 8: "WindGust", 9: "WindDir",
                  10: "InsideHumidity", 11: "OutsideHumidity",
                  12: "InsideTemp", 13: "OutsideTemp",
                  14: "Pressure",
                  15: "TotalRain", 16: "DailyRain", 17: "HourlyRain",
                  18: "ConditionFlag", 25: "Evapotranspiration",
                  26: "UVIndex", 27: "SolarRadiation",
                  28: "WindChill",
                  29: "IndoorHeatIndex", 30: "OutdoorHeatIndex",
                  31: "Dewpoint", 32: "RainRate",
                  33: "OutdoorTempRate", 34: "IndoorTempRate",
                  35: "PressureRate",
                  36: "Channel1TempRate", 37: "Channel2TempRate",
                  38: "Channel3TempRate"}

    # Since this data file has fixed (terrible) units, convert them to metric
    #   in groups of similar conversions.  Must match keys above!
    # mph2ms = ["WindSpeed", "WindGust"]
    # f2c = ["InsideTemp", "OutsideTemp", "IndoorHeatIndex", "OutdoorHeatIndex",
    #        "Dewpoint", "OutdoorTempRate", "IndoorTempRate",
    #        "Channel1TempRate", "Channel2TempRate", "Channel3TempRate"]
    # in2mbar = ["Pressure", "PressureRate"]
    # in2mm = ["TotalRain", "DailyRain", "HourlyRain", "RainRate"]

    allfields = msg.split(",")

    if len(allfields) != 41:
        print("Wrong number of fields for a VirtualWeatherStation CSV!")
        fields = {}
    else:
        # Grab the date and time first
        datadate = "%s-%s-%s" % (allfields[1], allfields[2], allfields[3])
        datatime = "%s:%s:%s" % (allfields[4], allfields[5], allfields[6])

        dtstr = "%sT%s" % (datadate, datatime)
        dtobj = dt.strptime(dtstr, "%Y-%m-%dT%H:%M:%S")

        # You *need* to do this in this exact way; datetime.replate(tzinfo)
        #   will give weird results like a timezone offset of -07:28 !
        # thisTZ needs to be the timezone of the machine where the data file
        #   was written, and since it's Windows it's likely to be local time.
        dtobj_aware = thisTZ.localize(dtobj)
        # dtobj_utc = dtobj_aware.astimezone(pytz.UTC)

        # Start to assemble the output dictionary.
        fields = {"timestampdt": dtobj_aware,
                  "influx_ts_s": round(dtobj_aware.timestamp())}

        for each in storageMap:
            fields.update({storageMap[each]: float(allfields[each])})

    root = {rootname: fields}
    if fields != {}:
        npacket = xmld.unparse(root, pretty=True)

    return npacket
