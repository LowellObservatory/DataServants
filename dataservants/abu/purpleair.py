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

import time
import datetime as dt

import pytz
import requests

from ligmos.utils.database import influxobj
from ligmos.utils.packetizer import makeInfluxPacket


def keymap(devType="PurpleAir_PA-II"):
    """
    This maps the JSON fields from the PurpleAir sensor into something
    that's a little easier to interact with on the frontend.  The
    organization is:
      - key == metric
      - value[0] dict of tag names and values
      - value[1] list of associated data keys returned from device itself
    Instead of mapping everything, I just map the specific fields
    for sensors A & B and the rest are dumped into a 'info' tag.

    NOTE: _b postfixes are stripped out since it's handled better with tags

    devType, SensorID, DateTime and some others are turned into tags and
    generally handled manually to make sure the data doesn't get mixed
    if you do multiple database postings instead of one big one
    """
    if devType.lower() == "purpleair_pa-ii":
        pks = {'aqi': [{'sensor': 'A'}, ['p25aqic', 'pm2.5_aqi']],
               'aqi_b': [{'sensor': 'B'}, ['p25aqic_b', 'pm2.5_aqi_b']],
               'volumetric': [{'sensor': 'A'}, ['p_0_3_um',
                                                'p_0_5_um',
                                                'p_1_0_um',
                                                'p_2_5_um',
                                                'p_5_0_um',
                                                'p_10_0_um']],
               'volumetric_b': [{'sensor': 'B'}, ['p_0_3_um_b',
                                                  'p_0_5_um_b',
                                                  'p_1_0_um_b',
                                                  'p_2_5_um_b',
                                                  'p_5_0_um_b',
                                                  'p_10_0_um_b']],
               'pm_atm': [{'sensor': 'A'}, ['pm1_0_atm',
                                            'pm2_5_atm',
                                            'pm10_0_atm']],
               'pm_atm_b': [{'sensor': 'B'}, ['pm1_0_atm_b',
                                              'pm2_5_atm_b',
                                              'pm10_0_atm_b']],
               'pm_cf1': [{'sensor': 'A'}, ['pm1_0_cf_1',
                                            'pm2_5_cf_1',
                                            'pm10_0_cf_1']],
               'pm_cf1_b': [{'sensor': 'B'}, ['pm1_0_cf_1_b',
                                              'pm2_5_cf_1_b',
                                              'pm10_0_cf_1_b']]
               }
    else:
        pks = None

    return pks


def purpleQuery(ip, devType="PurpleAir_PA-II"):
    pks = keymap(devType=devType)
    # Defaults for aborted return values
    sensorid = None
    allSets = {}
    timestampDT = None
    postfix = "_b"
    tzstr = 'US/Arizona'
    localTZ = pytz.timezone(tzstr)

    endpoint = "http://%s/json?live=false" % (ip)
    try:
        print(endpoint)
        msg = requests.get(endpoint, timeout=10.)
    except Exception as err:
        print(str(err))
        # TODO: Catch the right exception
        msg = None

    # Note that the and is mostly useless, but lets me stub in some
    #   modifications if there is a different one in the future
    if devType.lower() == "purpleair_pa-ii":
        try:
            rjson = msg.json()
            # Now remap and reorganize the dict
            allSets = {}

            # Grab the important stuff to post it to the DB correctly
            #   These are hardcoded, but could be configurable
            sensormac = rjson.pop("SensorId")
            # sensorid = rjson.pop("Id")
            sensorname = rjson.pop("Geo")
            sensortype = rjson.pop("hardwarediscovered")

            basetags = {"sensormac": sensormac, "sensorname": sensorname,
                        "sensortype": sensortype}

            timestampStr = rjson.pop("DateTime")
            timestampDT = dt.datetime.strptime(timestampStr,
                                               "%Y/%m/%dT%H:%M:%Sz")
            # Add in the timezone by hand to make sure it's UTC
            timestampDT = timestampDT.replace(tzinfo=pytz.UTC)
            # Localize to our timezone; this might depend on your server?
            localTZ = pytz.UTC
            timestampDT = timestampDT.astimezone(localTZ)
            print(timestampDT)

            for bucket in pks:
                # bucket is the metric
                thisSet = {}

                # Explicitly make a copy and add to that so I can reuse the
                #   basetags at the very end
                tags = basetags.copy()
                # pks[bucket][0] are the tags
                tags.update(pks[bucket][0])

                # We want to loop over the data keys
                for key in pks[bucket][1]:
                    # print(key, rjson[key])
                    if key.endswith(postfix):
                        storeKey = key[:-len(postfix)]
                    else:
                        storeKey = key

                    thisSet.update({storeKey: rjson.pop(key)})
                print("values:", thisSet)
                print("tags:", tags)
                allSets.update({bucket: [tags, thisSet]})
            print("Done with bulk tagging")

            # At this point since we pop() above, the remaining keys
            #   are the "informational" ones so add them in too
            # BUT we must check a few keys for weird values that can
            #   happen as they're booting up
            if rjson['Adc'] == 'nan':
                rjson['Adc'] = -9999.9

            allSets.update({"metadata": [basetags, rjson]})
        except Exception as err:
            print("Well shit")
            print(str(err))

        # Now format the actual packets to be sent out over the broker
        pkt = purpleDBprep(timestampDT, allSets)

    return timestampDT, allSets


def purpleDBprep(timestamp, chunks):
    postfix = "_b"
    for metric in chunks.keys():
        tags = chunks[metric][0]
        vals = chunks[metric][1]

        # Remove metric postfix for sensor B that we kept as a hack.
        #   Do this *after* we grab the tags and vals using the stored name!
        if metric.endswith(postfix):
            metric = metric[:-len(postfix)]

        # ts = round(timestamp.timestamp()*1e3)
        ts = round(float(timestamp.strftime("%s.%f"))*1e3)

        # Convert the datetime timestamp to something influxdb will understand
        pkt = makeInfluxPacket(meas=[metric], fields=vals,
                               tags=tags, ts=ts)
        print(pkt)

    return pkt


if __name__ == "__main__":
    ip = ["10.11.131.55"]
    loopTimer = 60.
    devType = 'PurpleAir_PA-II'

    # dbhost = "10.10.130.138"
    # dbport = 8086
    # dbuser = 'darmok'
    # dbpass = 'jalad'
    # dbtable = 'airquality'

    # idb = influxobj(host=dbhost, port=dbport, tablename=dbtable,
    #                 user=dbuser, pw=dbpass, connect=True)

    while True:
        if isinstance(ip, list):
            for sensip in ip:
                print("Querying PurpleAir sensor ...")
                timestampDT, allSets = purpleQuery(sensip, devType=devType)

                # if allSets != {}:
                    # pStatus = purpleDBPoster(timestampDT, allSets, idb)

        print("Sleeping for %d seconds ..." % (loopTimer))
        time.sleep(loopTimer)
