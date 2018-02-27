# -*- coding: utf-8 -*-
"""
  This Source Code Form is subject to the terms of the Mozilla Public
  License, v. 2.0. If a copy of the MPL was not distributed with this
  file, You can obtain one at http://mozilla.org/MPL/2.0/.

  Created on Tue Feb 27 16:09:25 2018

  @author: rhamilton
"""

from __future__ import division, print_function, absolute_import

import os
from os.path import basename

import numpy as np
import datetime as dt
from collections import OrderedDict

from .. import utils


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
