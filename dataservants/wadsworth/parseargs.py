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

import argparse as argp


def parseArguments(prog=None):
    """Setup command line arguments that Wadsworth will use.
    """

    fclass = argp.ArgumentDefaultsHelpFormatter

    parser = argp.ArgumentParser(description='Wadsworth: The Data Butler',
                                 formatter_class=fclass,
                                 prog=prog)

    parser.add_argument('-c', '--config', metavar='/path/to/file.conf',
                        type=str,
                        help='File for instrument configuration information',
                        default='./archiving.conf', nargs='?')

    parser.add_argument('-p', '--passes', metavar='/path/to/file.conf',
                        type=str,
                        help='File for instrument password information',
                        default='./passwords.conf', nargs='?')

    parser.add_argument('--rangeNew', type=int,
                        help='Age (days) of directory to be actively archived',
                        default=2, nargs="?")

    parser.add_argument('--rangeOld', type=int,
                        help='Age (days) beyond which directory is cleared',
                        default=21, nargs="?")

    parser.add_argument('--oldest', type=int,
                        help='Age (days) beyond which to ignore directories',
                        default=7300, nargs="?")

    parser.add_argument('--hashtype', type=str,
                        choices=['xx64', 'md5', 'sha1', 'sha256', 'sha512',
                                 'sha3_256', 'sha3_512'],
                        help='Type of hash to use for file integrity checks',
                        default="xx64")

    parser.add_argument('-l', '--log', metavar='/path/to/file.log', type=str,
                        help='File for logging of information/status messages',
                        default='/tmp/wadsworth.log', nargs='?')

    parser.add_argument('-k', '--kill', action='store_true',
                        help='Kill an already running instance of Wadsworth',
                        default=False)

    # Note: Need to specify dest= here since there are multiple long options
    #   (and I prefer the fun option name in the code)
    lhtext = 'Kill another Wadsworth instance, then take its place'
    parser.add_argument('-r', '--restart', '--fratricide', action='store_true',
                        help=lhtext, dest='fratricide',
                        default=False)

    parser.add_argument('-n', '--nlogs', type=int,
                        help='Number of previous logs to keep after rotation',
                        default=30, nargs=1)

    parser.add_argument('--debug', action='store_true',
                        help='Print extra debugging messages while running',
                        default=False)

    args = parser.parse_args()

    return args


if __name__ == "__main__":
    parser, args = parseArguments(prog="Wadsworth.py")
