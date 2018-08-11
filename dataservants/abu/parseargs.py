# -*- coding: utf-8 -*-
#
#   This Source Code Form is subject to the terms of the Mozilla Public
#   License, v. 2.0. If a copy of the MPL was not distributed with this
#   file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on Thu Apr 19 11:41:18 GMT+7 2018
#
#  @author: rhamilton

from __future__ import division, print_function, absolute_import

import argparse as argp


def parseArguments(prog=None):
    """Setup command line arguments that Abu will use.
    """
    fclass = argp.ArgumentDefaultsHelpFormatter

    parser = argp.ArgumentParser(description='Abu: The Kleptomaniac Scraper',
                                 formatter_class=fclass,
                                 prog=prog)

    parser.add_argument('-c', '--config', metavar='/path/to/file.conf',
                        type=str,
                        help='File for instrument configuration information',
                        default='./abu.conf', nargs='?')

    parser.add_argument('-p', '--passes', metavar='/path/to/file.conf',
                        type=str,
                        help='File for instrument password information',
                        default='./passwords.conf', nargs='?')

    parser.add_argument('-l', '--log', metavar='/path/to/file.log', type=str,
                        help='File for logging of information/status messages',
                        default='/tmp/abu.log', nargs='?')

    parser.add_argument('-k', '--kill', action='store_true',
                        help='Kill an already running instance of Abu',
                        default=False)

    # Note: Need to specify dest= here since there are multiple long options
    #   (and I prefer the fun option name in the code)
    lhtext = 'Kill another Abu instance, then take its place'
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
    parser, args = parseArguments(prog="Abu.py")
