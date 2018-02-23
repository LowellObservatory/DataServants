import numpy as np
import datetime as dt

from influxdb import InfluxDBClient
from influxdb.exceptions import InfluxDBClientError


def openDB(dbname, host='localhost', port=8086, user='root', pw='root'):
    """
    """
    try:
        client = InfluxDBClient(host, port, username=user,
                                password=pw, database=dbname)
    except Exception as err:
        print(str(err))

    return client
    

if __name__ == "__main__":
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

    dbname = 'beeeeees'
    client = openDB(dbname)

    # Actually try to write some points, it'll barf if the database
    #   doesn't actually exist yet so create it if needed
    try:
        client.write_points(json_body)
    except InfluxDBClientError:
        client.create_database(dbname)
        client.write_points(json_body)

    result = client.query('select value from cpu_load_short;')
    print("Result: {0}".format(result))

    client.close()
