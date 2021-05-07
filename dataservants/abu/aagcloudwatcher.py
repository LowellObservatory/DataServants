# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 28 Apr 2021
#
#  @author: rhamilton

"""One line description of module.

Further description.
"""

from __future__ import division, print_function, absolute_import

from datetime import datetime as dt

import pytz
import xmltodict as xmld


def aagcloudwatcher(msg,
                    rootname="AAGCloudWatcher",
                    timezone='US/Arizona'):
    """
    """
    # Default return value
    npacket = ''

    # File date/time timezone object that we'll need for later
    thisTZ = pytz.timezone(timezone)

    # Since we read it in as lines() split it into two lines so we can grab
    #   the header lines first
    twolines = msg.strip().split("\n")
    if len(twolines) == 0:
        print("Empty file!")
        fields = {}
        allfields = []
    else:
        headers = twolines[0].replace('"', '').replace(" ", "").split(",")
        allfields = twolines[1].replace('"', '').replace(" ", "").split(",")

    if len(allfields) != 20:
        print("Wrong number of fields for a AAGCloudWatcher file!")
        fields = {}
    else:
        # Pop off the stuff we're working with
        datadate = allfields.pop(0)
        datatime = allfields.pop(0)
        headers = headers[2:]

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

        for i, col in enumerate(headers):
            # Stupid, but it works and is readable.
            oval = allfields[i]

            # Some special handling
            if oval == '':
                val = None
            elif col == 'RainHeatingPercentage':
                val = float(oval[:-1])
            else:
                try:
                    val = float(oval)
                except ValueError:
                    # This implies it was a string, so just store it that way
                    #   so I can skip the conditional checks for all the
                    #   potential string types
                    val = oval

            if val is not None:
                fields.update({col: val})

    root = {rootname: fields}
    if fields != {}:
        npacket = xmld.unparse(root, pretty=True)

    return npacket
