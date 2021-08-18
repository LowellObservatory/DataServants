# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 28 Jun 2019
#
#  @author: rhamilton

"""One line description of module.

Further description.
"""

from __future__ import division, print_function, absolute_import

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


def parserPurpleAir(rP, db=None):
    # rP == [meas, ts, timeprec, fields]
    meas = rP[0]
    ts = rP[1]
    timeprec = rP[2]
    rjson = rP[3]
    # Defaults for aborted return values
    allSets = {}
    postfix = "_b"

    # Note that the and is mostly useless, but lets me stub in some
    #   modifications if there is a different one in the future
    if rjson is not None and rjson['deviceType'].lower() == "purpleair_pa-ii":
        # Get the mapping needed for the database
        pks = keymap(devType=rjson['deviceType'])
        try:
            # Grab the important stuff to post it to the DB correctly
            #   These are hardcoded, but could be configurable
            sensormac = rjson.pop("SensorId")
            # sensorid = rjson.pop("Id")
            sensorname = rjson.pop("Geo")
            sensortype = rjson.pop("hardwarediscovered")

            basetags = {"sensormac": sensormac, "sensorname": sensorname,
                        "sensortype": sensortype}

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

            allSets.update({"metadata": [basetags, rjson]})
        except Exception as err:
            print("Well shit")
            print(str(err))

        if allSets != {}:
            purpleDBprep(ts, timeprec, allSets, db=db)

    return allSets


def purpleDBprep(ts, timeprec, allSets, db=None):
    postfix = "_b"
    for metric in allSets.keys():
        tags = allSets[metric][0]
        vals = allSets[metric][1]

        # Remove metric postfix for sensor B that we kept as a hack.
        #   Do this *after* we grab the tags and vals using the stored name!
        if metric.endswith(postfix):
            metric = metric[:-len(postfix)]

        # Convert the datetime timestamp to something influxdb will understand
        pkt = makeInfluxPacket(meas=[metric], fields=vals,
                               tags=tags, ts=ts)
        print(pkt)

        # Actually commit the packet. singleCommit opens it,
        #   writes the packet, and then optionally closes it.
        if db is not None:
            db.singleCommit(pkt, timeprec=timeprec,
                            table=db.tablename, close=True)
