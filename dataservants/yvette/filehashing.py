# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on Tue Feb 27 16:09:25 2018
#
#  @author: rhamilton

"""Yvette's logic to make and check hashes of files.

Actual hashing functions can be found in :mod:`dataservants.utils.hashes`.
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
    """Create a CSV manifest of files,hashval for files matching `filetype`.

    Given a directory, recursively look for all files matching filetype. Look
    for an existing hashfile ``AListofHashes`` with extension ``htype`` and
    compare the files found against the files in that CSV list.

    .. warning::
        The hash file name is hardcoded to
        ``AListofHashes`` with extension ``htype``. The code won't search
        for other types, so don't switch unless it's **absolutely** necessary
        because your old/existing hash files would be ignored and the
        code will make new ones of the new ``htype``!

    If the list isn't found, all files are hashed and the file is written
    (but **NOT** in this function).  If the list is found, hash only the
    uniquely found files not in the CSV list.  Return a full dict of files
    and their hash value to the calling function so the hashfile can be
    written from there.

    Args:
        mdir (:obj:`str`)
            Directory to look for files
        htype (:obj:`str`, optional)
            Hashing function type. See the list of allowed values in
            :func:`dataservants.yvette.parseargs.setup_arguments`
        bsize (:obj:`int`, optional)
            Hashing function bite size in bytes. Defaults to 2**25 or
            33554432 bits (a.k.a. 4 MiB).
        filetype (:obj:`str`)
            Wildcard string to match files. Defaults to "*.fits".
        debug (:obj:`bool`)
            Bool to trigger additional debugging outputs. Defaults to False.

    Returns:
        existingHashes (:obj:`dict`)
            Dictionary of hashed files, old and new, keyed to their full path.

            .. code-block:: python

                existingHashes = {'/mnt/lemi/lois/20140619/lmi.0001.fits':
                                  '518eab9e1cbaf628',
                                  '/mnt/lemi/lois/20140619/lmi.0002.fits':
                                  'ceabecd38c8b4010',
                                  '/mnt/lemi/lois/20140619/lmi.0003.fits':
                                  'bc0c46fff7a10fa5'}
    """
    # Find all the files matching filetype at and underneath mdir
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
    hfname = mdir + "/AListofHashes." + htype
    existingHashes = utils.hashes.readHashFile(hfname)

    unq = []
    if existingHashes == {}:
        if debug is True:
            print("Hash file invalid or not found; making a new one!")
            print("Hashes stored in: %s" % (hfname))
        unq = ff
    else:
        doneFiles = existingHashes.keys()
        if debug is True:
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

        # We just care about just the actual hash value, not the hash obj.
        newKeys = OrderedDict(zip(unq, [h.hexdigest() for h in hs]))

    # The above loop, if there are files to do, will return the dict
    #   of just the new files; need to append them to the old ones too
    #   A little janky since I want to still keep the old stuff first
    #   in the ordered dict. Could be written clearer
    existingHashes.update(newKeys)

    return existingHashes


def verifyFiles(mdir, htype='xx64', bsize=2**25,
                filetype="*.fits", debug=False):
    """Verify file hashes against those in a given list.

    Given a directory, recursively look for all files matching filetype
    and calculate their hashes.  It stores the hashes in a dict
    keyed to the filename, which is then compared to the hash file read in
    from ``hfname``.  The two are compared by the basename of their keys to
    allow for mounting/storage path differences.  A list of files in the given
    directory that fail the check is returned.

    .. warning::
        The hash file name is hardcoded to
        ``AListofHashes`` with extension ``htype``. The code won't search
        for other types, so don't switch unless it's **absolutely** necessary
        because your old/existing hash files would be ignored and the
        code will make new ones of the new ``htype``!

    Args:
        mdir (:obj:`str`)
            Directory to look for files
        htype (:obj:`str`, optional)
            Hashing function type. See the list of allowed values in
            :func:`dataservants.yvette.parseargs.setup_arguments`
        bsize (:obj:`int`, optional)
            Hashing function bite size in bytes. Defaults to 2**25 or
            33554432 bits (a.k.a. 4 MiB).
        filetype (:obj:`str`)
            Wildcard string to match files. Defaults to "*.fits".
        debug (:obj:`bool`)
            Bool to trigger additional debugging outputs. Defaults to False.

    Returns:
        mismatch (:obj:`list`)
            List of files in the given directory ``mdir`` that do not match
            the hashfile found in that same ``mdir``

    .. note::
        I admit that this function could probably be 1/2 as short by just
        calling :func:`dataservants.yvette.filehashing.makeManifest` with
        a special option, and should probably be refactored to do just that.
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
    hfname = mdir + "/AListofHashes." + htype

    existingHashes = utils.hashes.readHashFile(hfname,
                                               basenamed=True,
                                               debug=debug)
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
    # tf == testfile, ff == found files (in given directory)
    for tf in ff:
        testfile = basename(tf)
        try:
            if newKeys[testfile] != existingHashes[testfile]:
                # Store the full path to make retransfters easier!
                mismatch.append(tf)
        except KeyError as err:
            print(str(err))
            print("Hash of file %s doesn't have a comparison!" % (tf))

    return mismatch
