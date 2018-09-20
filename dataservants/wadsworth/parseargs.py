# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on Tue Feb 27 12:44:35 2018
#
#  @author: rhamilton

from __future__ import division, print_function, absolute_import


def extraArguments(parser):
    """ADDITIONAL command line arguments that Wadsworth will use.

    Implies that they already contain the default set so there's no
    setup of the parser details/format/whatever.

    If there are none, it just returns the parser unchanged.
    """

    nhstr = 'Maximum age (days) of directory to still be actively archived'
    parser.add_argument('--rangeNew', type=int,
                        help=nhstr,
                        default=2, nargs="?")

    ohstr = 'Maximum age (days) of a directory before it will be cleared'
    parser.add_argument('--rangeOld', type=int,
                        help=ohstr,
                        default=21, nargs="?")

    parser.add_argument('--oldest', type=int,
                        help='Age (days) beyond which to ignore directories',
                        default=180, nargs="?")

    parser.add_argument('--hashtype', type=str,
                        choices=['xx64', 'md5', 'sha1', 'sha256', 'sha512',
                                 'sha3_256', 'sha3_512'],
                        help='Type of hash to use for file integrity checks',
                        default="xx64")

    return parser
