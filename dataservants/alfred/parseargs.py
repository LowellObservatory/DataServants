# -*- coding: utf-8 -*-
#
#   This Source Code Form is subject to the terms of the Mozilla Public
#   License, v. 2.0. If a copy of the MPL was not distributed with this
#   file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on Mon Feb 26 11:37:03 2018
#
#  @author: rhamilton

from __future__ import division, print_function, absolute_import

import argparse as argp


def extraArguments(parser):
    """ADDITIONAL command line arguments that Iago will use.

    Implies that they already contain the default set so there's no
    setup of the parser details/format/whatever.

    If there are none, it just returns the parser unchanged.
    """

    # An example...
    # parser.add_argument('-q', '--quiddich', action='store_true',
    #                     help='Define a useless argument',
    #                     default=False)

    return parser
