# -*- coding: utf-8 -*-
"""
  This Source Code Form is subject to the terms of the Mozilla Public
  License, v. 2.0. If a copy of the MPL was not distributed with this
  file, You can obtain one at http://mozilla.org/MPL/2.0/.

  Created on Tue Jan 30 12:53:33 2018

  @author: rhamilton
"""

from __future__ import division, print_function, absolute_import

import sys
import json
import numpy as np
import datetime as dt

import os
from os.path import basename

# These two put is firmly in Python 2.7.x or above territory
import argparse as argp
from collections import OrderedDict

try:
    # This one might fail
    import xxhash
except ImportError:
    xxhash = None

from .. import utils


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


def makeManifest(mdir, htype='xx64', bsize=2**25,
                 filetype="*.fits", debug=False):
    """
    Given a directory, and a running dictionary of files already seen,
    create a CSV list of files that match the given
    extension and record both their location and their checksums.

    You don't get to control the location of the output manifest file. No.

    The hashtype is passed along to hashfunc and checked there; if it fails,
    it'll default to sha1 since that's a better performer for large files
    than md5. Blocksize is passed verbatim and not checked, which someone
    will probably tell me someday is a terrible idea at which point I'll agree.
    """
    ff = utils.files.recursiveSearcher(mdir, fileext=filetype)
    if len(ff) == 0:
        if debug is True:
            print("No files found!")
        return None

    # Need to convert to be in GiB right off the bat since some of the inst.
    #   host machines are 32-bit, and os.path.getsize() returns bytes, so
    #   sum(os.path.getsize()) will overrun the 32-bit val and go negative!
    sizes = [os.path.getsize(e)/1024./1024./1024. for e in ff]
    tsize = np.sum(sizes)
    if debug is True:
        print("Found %d files in %s" % (len(ff), mdir))
        print("Total of %.2f GiB" % (tsize))

    # Check to see if any of the files already have a valid hash
    #   BUT don't verify that has, assume that it's good for now
    hfname = mdir + "AListofHashes." + htype
    existingHashes = utils.hashes.readHashFile(hfname)
    unq = []
    if existingHashes == {}:
        if debug is True:
            print("Hash file invalid or not found; making a new one!")
            print("Hashes stored in: %s" % (hfname))
        unq = ff
    else:
        if debug is True:
            doneFiles = existingHashes.keys()
            print("%d files found in hashfile %s" % (len(doneFiles), hfname))
        # Check to see if the list of files found is different than the ones
        #   already in the hash file; if they're there already, remove them
        #   from the list and only operate on the ones that aren't there.
        unq = [f for f in ff if f not in doneFiles]
        if debug is True:
            print("%d new files found; ignoring others" % (len(unq)))

    # Actually perform the hashing, with a simple time monitor
    newKeys = {}
    if unq != []:
        if debug is True:
            print("Calculating hashes...")
        dt1 = dt.datetime.utcnow()
        # Potential for a big time sink here; consider a signal/alarm?
        hs = [utils.hashes.hashfunc(e, htype=htype,
                                    bsize=bsize, debug=debug) for e in unq]
        dt2 = dt.datetime.utcnow()
        telapsed = (dt2 - dt1).total_seconds()

        # For informational purposes{
        if debug is True:
            print("")
            print("Hashes completed in %.2f seconds" % (telapsed))
            print("%.5f seconds per file" % (telapsed/len(ff)))
            print("%.5f GiB/sec hash rate" % (tsize/telapsed))

        # Now make a dict of the results so we can work a little easier
        #   Two choices to the end user here:
        #   1) If you want to maintain the hash objects...
#        newKeys = OrderedDict(zip(unq, hs))

        #   2) If you care about just the actual hash value...
        newKeys = OrderedDict(zip(unq, [h.hexdigest() for h in hs]))

    # The above loop, if there are files to do, will return the dict
    #   of just the new files; need to append them to the old ones too
    #   A little janky since I want to still keep the old stuff first
    #   in the ordered dict. Could be written clearer
    existingHashes.update(newKeys)

    return existingHashes


def verifyFiles(mdir, htype='xx64', bsize=2**25,
                filetype="*.fits", debug=False):
    """
    Given a directory, and a running dictionary of files already seen, read
    the manifest file (default name) and re-check the files against the hashes
    seen in that manifest file. Return/flag files that fail the check so
    that they can be re-transferred.

    Looks a lot like makeManifest but decided to keep it seperate since
    it performs a different-enough function.
    """
    ff = utils.files.recursiveSearcher(mdir, fileext=filetype)
    if len(ff) == 0:
        if debug is True:
            print("No files found!")
        return None

    # Need to convert to be in GiB right off the bat since some of the inst.
    #   host machines are 32-bit, and os.path.getsize() returns bytes, so
    #   sum(os.path.getsize()) will overrun the 32-bit val and go negative!
    sizes = [os.path.getsize(e)/1024./1024./1024. for e in ff]
    tsize = np.sum(sizes)
    if debug is True:
        print("Found %d files in %s" % (len(ff), mdir))
        print("Total of %.2f GiB" % (tsize))

    # Read in the existing hash file
    hfname = mdir + "AListofHashes." + htype
    existingHashes = utils.hashes.readHashFile(hfname, basenamed=True)
    if debug is True:
        print("%d files found in hashfile %s" % (len(existingHashes), hfname))

    # Calculate the new hashes, with a simple time monitor
    newKeys = {}
    if ff != []:
        if debug is True:
            print("Calculating hashes...")
        dt1 = dt.datetime.utcnow()
        # Potential for a big time sink here; consider a signal/alarm?
        hs = [utils.hashes.hashfunc(e, htype=htype,
                                    bsize=bsize, debug=debug) for e in ff]
        dt2 = dt.datetime.utcnow()
        telapsed = (dt2 - dt1).total_seconds()

        # For informational purposes
        if debug is True:
            print("")
            print("Hashes completed in %.2f seconds" % (telapsed))
            print("%.5f seconds per file" % (telapsed/len(ff)))
            print("%.5f GiB/sec hash rate" % (tsize/telapsed))

        # Strip out path information to compare filename to filename
        bn = [basename(f) for f in ff]
        newKeys = OrderedDict(zip(bn, [h.hexdigest() for h in hs]))

    # Now compare the new against the old. Strip out path info again
    mismatch = []
    for tf in ff:
        testfile = basename(tf)
        if newKeys[testfile] != existingHashes[testfile]:
            # Store the full path to make retransfters easier!
            mismatch.update(tf)

    return mismatch


if __name__ == "__main__":
    rjson = {}

    # Setup argument parsing *before* logging so help messages go to stdout
    #   NOTE: This function sets up the default values when given no args!
    parser, args = setup_arguments()

    if len(sys.argv) == 1:
        parser.print_help()
    else:
        if args.debug is True:
            debug = True
        else:
            debug = False
        # Verify inputs; only do stuff if the directory is a valid one
        dirstatus, vdir = utils.files.checkDir(args.dir, debug=debug)
        if dirstatus is True:
            if args.look is True:
                ddirs = utils.files.getDirListing(vdir,
                                                  dirmask=args.regexp,
                                                  recently=args.rangeNew,
                                                  debug=debug)
                rjson.update({"NewDirs": ddirs})

            # Check for optional actions
            #   NOTE: None of these are exclusionary
            if args.freespace is True:
                frees = utils.files.checkFreeSpace(args.dir, debug=debug)
                rjson.update({"FreeSpace": frees})

            if args.clean is True:
                pass

            if args.hashtype == 'xx64':
                if xxhash is None:
                    print("XX64 hash unavailable; falling back to sha1")
                    args.hashtype = 'sha1'

            if args.hashtype == 'md5':
                print("Warning: MD5 is slow! Consider another option!")

            if args.pack is True:
                # Create a manifest dict
                md1 = makeManifest(args.dir, filetype=args.filetype,
                                   htype=args.hashtype, debug=debug)
                # Write it, and return the filename
                hfname = utils.hashes.writeHashFile(md1, args.dir,
                                                    htype=args.hashtype,
                                                    debug=debug)
                # Return logging
                rjson.update({"HashFile": hfname})

                # Now read it back in for some debug checking
                if debug is True:
                    print()
                    md2 = utils.hashes.readHashFile(hfname, debug=debug)
                    print("MD1 == MD2?\n%s" % (md1 == md2))
                    print()

                # Verification step
                broken = verifyFiles(args.dir, filetype=args.filetype,
                                     htype=args.hashtype, debug=debug)
                rjson.update({"FailedVerification": broken})
        else:
            print("%s doesn't exist or isnt' readable" % (args.dir))

    print(json.dumps(rjson))
