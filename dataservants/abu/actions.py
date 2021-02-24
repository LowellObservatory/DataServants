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

import json

import pytz
import xmltodict as xmld


def amqStats(msg):
    pass


def prepWU(config, vals, tstamp):
    # See also:
    #
    # https://support.weather.com/s/article/PWS-Upload-Protocol?language=en_US
    #
    # Note that I'm setting units=e (English) up here already
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
    #   fields in wxinfo; WUnderground API keys are first.
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

    if returnDict is True:
        # We return valdict here because the station name is unimportant
        #   for what this will be used for (e.g. republishing online)
        return npacket, valdict
    else:
        return npacket


def parseiSense(msg, rootKey=None):
    """
    Translate the "XML" file that the i-SENSE voltage monitor puts out
    into something that fits easier into the XML schema/parsing way of life.
    """
    pdict = xmld.parse(msg)

    # There's only ever one root, so just cut to the chase
    pdict = pdict['attributes']

    if rootKey is None:
        rootKey = "isense"

    # Since this is eventually going to become XML, we need to define a root
    #   key for the document; all other tags will live under it
    root = {rootKey: None}

    # Now loop over each individual measurement in the orig. crap packet
    valdict = {}
    for imeas in pdict['attribute']:
        mn = imeas['@id']
        try:
            mv = imeas['#text']
        except KeyError:
            # This means that the attribute had no actual value
            mv = ""

        newEntry = {mn: mv}

        valdict.update(newEntry)

    # Add our values to this station
    root[rootKey] = valdict

    # Now turn it into an XML string so we can pass it along to the broker
    #   using the magic that is xmld's unparse() method
    npacket = xmld.unparse(root, pretty=True)

    return npacket
