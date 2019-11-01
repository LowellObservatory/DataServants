# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 8 Sep 2019
#
#  @author: rhamilton

"""One line description of module.

Further description.
"""

from __future__ import division, print_function, absolute_import


def parse_deboned_LOISTemps(logmsg):
    """
    A stripped down version of the original living over in Mr. Freeze,
    but since he's not awake yet I need this here as a shim.
    """
    fields = {}
    if logmsg.startswith("CCD sensor adus"):
        # print("Parsing: %s" % (logmsg))
        # CCD sensor adus temp1 2248 temp2 3329 set1 2249 heat1 2016'
        adutemp1 = int(logmsg.split(" ")[4])
        adutemp2 = int(logmsg.split(" ")[6])
        aduset1 = int(logmsg.split(" ")[8])
        aduheat1 = int(logmsg.split(" ")[10])

        fields = {"aduT1": adutemp1}
        fields.update({"aduT2": adutemp2})
        fields.update({"aduT2": adutemp2})
        fields.update({"aduS1": aduset1})
        fields.update({"aduH1": aduheat1})

        # print(adutemp1, adutemp2, aduset1, aduheat1)
    elif logmsg.startswith("CCD Heater"):
        # NOTE! This one will have had a ":" removed by the
        #   logmsg creation line above, so you can just split normally
        # print("Parsing: %s" % (logmsg))
        # CCD Heater Values:1.21 0.00
        heat1 = float(logmsg.split(" ")[3])
        heat2 = float(logmsg.split(" ")[4])

        fields = {"H1": heat1}
        fields.update({"H2": heat2})

        # print(heat1, heat2)
    elif logmsg.startswith("CCD Temp"):
        # Same as "CCD Heater" in that ":" have been removed by this point
        # print("Parsing: %s" % (logmsg))
        # CCD Temp -110.06 18.54 Setpoints -109.95 0.00 '
        temp1 = float(logmsg.split(" ")[2])
        temp2 = float(logmsg.split(" ")[3])
        set1 = float(logmsg.split(" ")[5])
        set2 = float(logmsg.split(" ")[6])

        fields = {"T1": temp1}
        fields.update({"T2": temp2})
        fields.update({"S1": set1})
        fields.update({"S2": set2})
        fields.update({"T1S1delta": temp1-set1})

        # print(temp1, temp2, set1, set2)
    else:
        # fields needs to be set to None rather than {} because further
        #   packet checks will look for None! You'll get empty (invalid)
        #   packets being put into the database otherwise.
        fields = None
        # print(loglevel, logmsg)

    return fields
