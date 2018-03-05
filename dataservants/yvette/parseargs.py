# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on Tue Feb 27 16:06:23 2018
#
#  @author: rhamilton

from __future__ import division, print_function, absolute_import

import argparse as argp


def setup_arguments():
    """
    Setup command line arguments that could be used if so desired.
    """

    fclass = argp.ArgumentDefaultsHelpFormatter

    parser = argp.ArgumentParser(description='Yvette: The Data Maid',
                                 formatter_class=fclass)

    parser.add_argument(dest='dir', metavar='/path/to/data/',
                        type=str,
                        help='Path to perform further operations/options',
                        default='~/', nargs='?')

    parser.add_argument('-l', '--look', action='store_true',
                        help='Look for new data directories matching regexp',
                        default=False)

    parser.add_argument('--rangeNew', type=int,
                        help='Age (days) of directory to be actively archived',
                        default=3, nargs="?")

    parser.add_argument('--rangeOld', type=int,
                        help='Age (days) beyond which directory is cleared',
                        default=30, nargs="?")

    parser.add_argument('-r', '--regexp', type=str,
                        help='Regular expression for finding data directories',
                        default="[0-9]{8}.", nargs='?')

    parser.add_argument('-c', '--clean', action='store_true',
                        help='Clean up old data',
                        default=False)

    hstr = 'Create data manifests for filetypes with hashtype'
    parser.add_argument('-p', '--pack', action='store_true',
                        help=hstr,
                        default=False)

    parser.add_argument('--filetype', type=str,
                        help='Mask for finding data',
                        default="*.fits")

    parser.add_argument('--hashtype', type=str,
                        choices=['xx64', 'md5', 'sha1', 'sha256', 'sha512',
                                 'sha3_256', 'sha3_512'],
                        help='Type of hash to use for file integrity checks',
                        default="xx64")

    parser.add_argument('-f', '--freespace', action='store_true',
                        help='Check amount of free space at ',
                        default=False)

    parser.add_argument('--debug', action='store_true',
                        help='Print extra debugging messages while running',
                        default=False)

    args = parser.parse_args()

    return parser, args
