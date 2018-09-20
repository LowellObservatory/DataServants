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


def setup_arguments(prog=None):
    """Setup command line arguments that Yvette will use.

    Yvette itself is intended to have minimal processing logic - it'll do
    what it is told/asked and it is up to the (remote) calling function to
    orchestrate the activities appropriately.
    """
    fclass = argp.ArgumentDefaultsHelpFormatter

    parser = argp.ArgumentParser(description='Yvette: The Data Maid',
                                 formatter_class=fclass,
                                 prog=prog)

    parser.add_argument(dest='dir', metavar='/path/to/data/',
                        type=str,
                        help='Path to perform further operations/options',
                        default='~/', nargs='?')

    parser.add_argument('-r', '--regexp', type=str,
                        help='Regular expression for finding data directories',
                        default="[0-9]{8}.*", nargs='?')

    parser.add_argument('--filetype', type=str,
                        help='Mask for finding data',
                        default="*.fits")

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
                        default=7300, nargs="?")

    parser.add_argument('--hashtype', type=str,
                        choices=['xx64', 'md5', 'sha1', 'sha256', 'sha512',
                                 'sha3_256', 'sha3_512'],
                        help='Type of hash to use for file integrity checks',
                        default="xx64")

    parser.add_argument('--debug', action='store_true',
                        help='Print extra debugging messages while running',
                        default=False)

    # This is an action, but doesn't need to be kept from acting w/the others
    parser.add_argument('-f', '--freespace', action='store_true',
                        help='Check amount of free space at specified dir',
                        default=False)

    parser.add_argument('--cpumem', action='store_true',
                        help='Check on CPU and RAM usage',
                        default=False)

    parser.add_argument('-l', '--look', action='store_true',
                        help='Look for new data directories matching regexp',
                        default=False)

    parser.add_argument('-o', '--old', action='store_true',
                        help='Look for data directories older than rangeOld',
                        default=False)

    parser.add_argument('--checkProcess', type=str,
                        help='Return stats for given process name',
                        default=None)

    # The actual actions are defined to be mutually exclusive, meaning
    #   only ONE of them will act per call to Yvette.
    #
    # This keeps things simple, and allows a more natural use of
    #   the 'dir' parameter as defined above rather than a dir per function
    grp1 = parser.add_mutually_exclusive_group(required=False)

    grp1.add_argument('-c', '--clean', action='store_true',
                      help='Check for directories that can be deleted',
                      default=False)

    hstr = 'Create data manifests for filetypes with hashtype'
    grp1.add_argument('-p', '--pack', action='store_true',
                      help=hstr,
                      default=False)

    grp1.add_argument('-v', '--verify', dest='verify', action='store_true',
                      help="Verify the hashes in the given directory",
                      default=False)

    # Let's never advertise this particular hand grenade. I will likely end up
    #   removing it because my gut is telling me it is a terrible effing idea
    grp2 = parser.add_mutually_exclusive_group(required=False)
    grp2.add_argument('--delete', action="store_true",
                      help=argp.SUPPRESS,
                      default=False)

    # Some hidden arguments that normal users shouldn't be screwing with
    parser.add_argument('--norepack', action='store_true',
                        help=argp.SUPPRESS,
                        default=False)

    # For creating large numbers of manifests
    grp3 = parser.add_mutually_exclusive_group(required=False)
    grp3.add_argument('--MegaMaid', action="store_true",
                      help=argp.SUPPRESS,
                      default=False)

    args = parser.parse_args()

    return parser, args


if __name__ == "__main__":
    parser, args = setup_arguments(prog="Yvette.py")
