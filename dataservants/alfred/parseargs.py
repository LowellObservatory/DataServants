# -*- coding: utf-8 -*-
"""
Created on Mon Feb 26 11:37:03 2018

@author: rhamilton
"""

from __future__ import division, print_function, absolute_import

import argparse as argp


def parseArguments():
    """
    Setup command line arguments that could be used if so desired.
    """

    fclass = argp.ArgumentDefaultsHelpFormatter

    parser = argp.ArgumentParser(description='Alfred: The Instrument Monitor',
                                 formatter_class=fclass)

    parser.add_argument('-c', '--config', metavar='/path/to/file.conf',
                        type=str,
                        help='File for instrument configuration information',
                        default='./alfred.conf', nargs='?')

    parser.add_argument('-p', '--passes', metavar='/path/to/file.conf',
                        type=str,
                        help='File for instrument password information',
                        default='./passwords.conf', nargs='?')

    parser.add_argument('-l', '--log', metavar='/path/to/file.log', type=str,
                        help='File for logging of information/status messages',
                        default='/tmp/alfred.log', nargs='?')

    parser.add_argument('-k', '--kill', action='store_true',
                        help='Kill an already running instance of Alfred',
                        default=False)

    # Note: Need to specify dest= here since there are multiple long options
    #   (and I prefer the fun option name in the code)
    lhtext = 'Kill another Alfred instance, then take its place'
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
