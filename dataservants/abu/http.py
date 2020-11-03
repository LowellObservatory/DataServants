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


from requests import get
from requests.exceptions import ConnectionError as RCE
from requests.auth import HTTPDigestAuth, HTTPBasicAuth


def webgetter(resourceloc, user=None, pw=None):
    """
    """
    if user or pw is not None:
        auth = HTTPBasicAuth(user, pw)
    else:
        auth = None

    url = "http://%s" % (resourceloc)
    data = get(url, auth=auth)
    # Check the HTTP response;
    #   200 - 400 == True
    #   400 - 600 == False
    #   Other way to do it might be to check if .status_code == 200
    if data.ok is True:
        print("Good grab!")
    else:
        # This will be caught elsewhere
        print("Bad grab :(")
        raise RCE

    return data.content
