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


from requests import get, post
from requests.exceptions import ConnectionError as RCE
from requests.auth import HTTPDigestAuth, HTTPBasicAuth


def webgetter(resourceloc, params=None, data=None, user=None, pw=None):
    """
    """
    if user or pw is not None:
        auth = HTTPBasicAuth(user, pw)
    else:
        auth = None

    resp = get(resourceloc, params=params, data=data, auth=auth)
    # Check the HTTP response;
    #   200 - 400 == True
    #   400 - 600 == False
    #   Other way to do it might be to check if .status_code == 200
    if resp.ok is True:
        print(resp.status_code)
        print(resp.text.strip())
        print("Good grab!")
    else:
        # This should be caught in the calling loop and handled appropriately
        print("Bad grab :(")
        print(resp.status_code)
        raise RCE

    return resp.content
