# -*- coding: utf-8 -*-
"""
  This Source Code Form is subject to the terms of the Mozilla Public
  License, v. 2.0. If a copy of the MPL was not distributed with this
  file, You can obtain one at http://mozilla.org/MPL/2.0/.

  Created on Thu Feb 22 20:05:07 2018

  @author: rhamilton
"""

from __future__ import division, print_function, absolute_import

import sys
import numpy as np
import datetime as dt

from requests.exceptions import ConnectionError

from influxdb import InfluxDBClient
from influxdb.exceptions import InfluxDBClientError


class influxobj():
    """
    Creates an InfluxDB database access object, specific to a database name.

    """
    def __init__(self, dbase, connect=True,
                 host='localhost', port=8086,
                 user='root', pw='root'):
        self.host = host
        self.port = port
        self.username = user
        self.password = pw
        self.dbase = dbase
        if connect is True:
            self.openDB()
        else:
            self.client = None

    def openDB(self):
        """
        """
        try:
            self.client = InfluxDBClient(self.host, self.port,
                                         username=self.username,
                                         password=self.password)
        except Exception as err:
            self.client = None
            print(str(err))

    def writeToDB(self, vals):
        """
        Given an opened InfluxDBClient, write stuff to the given dbname
        """
        # Make sure we're actually connected first
        if self.client is not None:
            # Actually try to write some points, it'll barf if the database
            #   doesn't actually exist yet so create it if needed
            try:
                print("Trying to write_points")
                self.client.write_points(vals)
            except ConnectionError as err:
                print("Fatal Connection Error!")
                print("Is InfluxDB running?")
                sys.exit(-1)
            except InfluxDBClientError:
                print("Failed to write_points")
                self.client.create_database(self.dbase)
                self.client.write_points(vals)
            except Exception as err:
                print(str(err))
                sys.exit(-1)
        else:
            print("Error: InfluxDBClient not connected!")
            sys.exit(-1)

    def closeDB(self):
        """
        """
        try:
            self.client.close()
        except Exception as err:
            print(str(err))

    def dropDB(self, imsure=False):
        """
        """
        if imsure is False:
            print("You're not sure! Doing nothing.")
        else:
            try:
                self.client.drop_database(self.dbase)
            except Exception as err:
                print(str(err))


def example():
    """
    """
    dbname = 'beeeeees'
    json_body = [
                 {
                  "measurement": "cpu_load_short",
                  "tags": {
                           "host": "server01",
                           "region": "us-west"
                          },
                  "time": dt.datetime.now(),
                  "fields": {
                             "value": np.random.normal(loc=1.0)
                            }
                 }
                ]

    # Calling with connect=True establishes the connection, which
    #   populates influxobj.client with the right stuff
    ifo = influxobj(dbname, connect=True)
    ifo.writeToDB(json_body)

    result = ifo.query('select value from cpu_load_short;')
    print("Result: {0}".format(result))

    ifo.closeDB()
