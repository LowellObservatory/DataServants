# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on Thu Feb 22 20:05:07 2018
#
#  @author: rhamilton

from __future__ import division, print_function, absolute_import

import sys
import numpy as np
import datetime as dt

from requests.exceptions import ConnectionError

try:
    import influxdb
    from influxdb import InfluxDBClient
    from influxdb.exceptions import InfluxDBClientError
except (ImportError, ModuleNotFoundError) as err:
    influxdb = None


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
        if connect is True and influxdb is not None:
            self.openDB()
        else:
            self.client = None

    def alterRetention(self, pname='Hold6w', duration='6w'):
        """
        """
        if influxdb is not None:
            try:
                self.client.alter_retention_policy(pname,
                                                   duration=duration,
                                                   default=True)
            except influxdb.exceptions.InfluxDBClientError:
                self.client.create_retention_policy(pname,
                                                    duration,
                                                    1,
                                                    default=True)

    def openDB(self):
        """
        """
        if influxdb is not None:
            try:
                self.client = InfluxDBClient(self.host, self.port,
                                             username=self.username,
                                             password=self.password,
                                             database=self.dbase)
                # Create the database if it doesn't exist; underneath the hood
                #   InfluxDB is basically doing
                #   CREATE DATABASE IF NOT EXISTS dbname
                self.client.create_database(self.dbase)
            except Exception as err:
                self.client = None
                print(str(err))
        else:
            print("InfluxDB-python not found!")

    def writeToDB(self, vals, debug=False):
        """
        Given an opened InfluxDBClient, write stuff to the given dbname.

        BUG: InfluxDB errors are getting returned, not caught. Don't know why.
        e.g.
        400: {"error":"field type conflict: input field \"ping\" on
              measurement \"PingResults\" is type integer, already exists as
              type float"}
        """
        # Make sure we're actually connected first
        if self.client is not None:
            # Actually try to write some points, it'll barf if the database
            #   doesn't actually exist yet so create it if needed
            try:
                if debug is True:
                    print("Trying to write_points")
                self.client.write_points(vals)
            except ConnectionError as err:
                print("Fatal Connection Error!")
                print("Is InfluxDB running?")
                sys.exit(-1)
            except InfluxDBClientError as err:
                if debug is True:
                    print("Failed to write_points")
                print(str(err))
                sys.exit(-1)
        else:
            print("Error: InfluxDBClient not connected!")
            sys.exit(-1)

    def closeDB(self):
        """
        """
        if self.client is not None:
            try:
                self.client.close()
            except Exception as err:
                print(str(err))

    def dropDB(self, imsure=False):
        """
        """
        if self.client is not None:
            if imsure is False:
                print("You're not sure! Doing nothing.")
            else:
                try:
                    self.client.drop_database(self.dbase)
                except Exception as err:
                    print(str(err))
