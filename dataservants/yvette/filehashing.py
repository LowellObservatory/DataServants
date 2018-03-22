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


def MegaMaid(loc, dirmask="[0-9]{8}.*", filetype="*.fits",
             youngest=20, oldest=7300, htype='xx64', debug=False):
    """
    Create a whole buttload of data manifests, one by one.

    This wraps up a lot of individual stuff into one easy-to-call function.
    """
    oldies = utils.files.getDirListing(loc, dirmask=dirmask,
                                       window=youngest,
                                       oldest=oldest,
                                       comptype='older',
                                       debug=debug)

    results = {}

    for odir in oldies:
        hfname = odir + "/AListofHashes." + htype
        hashes = makeManifest(odir, htype=htype,
                              filetype=filetype,
                              debug=debug)
        if hashes is not None:
            status = utils.hashes.writeHashFile(hashes, hfname,
                                                debug=debug)
        else:
            status = False

        cres = {hfname: status}
        results.update(cres)
        if debug is True:
            print(cres)

    return results


def getListFilesSizes(mdir, filetype="*.fits", debug=False):
    """Get a list of directories and the size of each file matching filetype.

    Args:
        mdir (:obj:`str`)
            Directory to look for files
        filetype (:obj:`str`, optional)
            Wildcard string to match files. Defaults to "*.fits".
        debug (:obj:`bool`, optional)
            Bool to trigger additional debugging outputs. Defaults to False.

    Returns:
        ff (:obj:`list`)
            List of files underneath ``mdir`` that match the regular expression
            given by ``filetype``, sorted by name.
        sizes (:obj:`list`)
            List of sizes of each file in ``ff``, in GiB. Need to have them
            in GiB to make sum(sizes) not overrun 32-bit limits.
    """
    # Find all the files matching filetype at and underneath mdir
    ff = utils.files.recursiveSearcher(mdir, fileext=filetype)
    if len(ff) == 0:
        # No files found, so return None for both ff and sizes to show this
        return None, None

    # Need to convert to be in GiB right off the bat since some of the inst.
    #   host machines are 32-bit, and os.path.getsize() returns bytes, so
    #   sum(os.path.getsize()) will overrun the 32-bit val and go negative!
    sizes = [os.path.getsize(e)/1024./1024./1024. for e in ff]
    tsize = np.sum(sizes)
    if debug is True:
        print("Found %d files in %s" % (len(ff), mdir))
        print("Total of %.2f GiB" % (tsize))

    return ff, sizes


def checkMismatches(flist, htype='xx64', bsize=2**25, debug=False):
    """
    """
    pass


def makeManifest(mdir, htype='xx64', bsize=2**25,
                 filetype="*.fits", forcerecheck=False,
                 fullpath=True, debug=False):
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
        filetype (:obj:`str`, optional)
            Wildcard string to match files. Defaults to "*.fits".
        forcerecheck (:obj:`bool`, optional)
            Bool to trigger calculation of all the hashes again.
            Defaults to False.  If true, the existing hash file is ignored.
        fullpath (:obj:`bool`, optional)
            Bool to trigger whether the returned dict has keys giving the
            full path of the file that was hashed (True) or whether it is
            basenamed first (False). Defaults to True.
        debug (:obj:`bool`, optional)
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
    ff, sizes = getListFilesSizes(mdir, filetype=filetype, debug=debug)
    tsize = np.sum(sizes)

    # If there's no files, there's nothing to do.
    if ff is None:
        return None

    if forcerecheck is False:
        # Check to see if any of the files already have a valid hash
        #   BUT don't verify that has, assume that it's good for now
        hfname = mdir + "/AListofHashes." + htype
        existingHashes = utils.hashes.readHashFile(hfname, basenamed=False)
        existingFiles = [basename(each) for each in existingHashes.keys()]
        if debug is True:
            print("%d files in hashfile %s" % (len(existingFiles), hfname))
    else:
        existingHashes = {}

    unq = []
    if existingHashes == {}:
        unq = ff
    else:
        # Check to see if the list of files found is different than the ones
        #   already in the hash file; if they're there already, remove them
        #   from the list and only operate on the ones that aren't there.
        unq = [f for f in ff if basename(f) not in existingFiles]
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

    returnDict = {}
    if fullpath is True:
        returnDict = existingHashes
    else:
        for fkey in existingHashes.keys():
            returnDict.update({basename(fkey): existingHashes[fkey]})

    return returnDict


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
    """
    # ff, sizes = getListFilesSizes(mdir, filetype=filetype, debug=debug)
    ff, _ = getListFilesSizes(mdir, filetype=filetype, debug=debug)

    # Read in the existing hash file
    hfname = mdir + "/AListofHashes." + htype

    # Keep full paths for clarity, but make a basenamed list for comparison
    existingHashes = utils.hashes.readHashFile(hfname,
                                               basenamed=False,
                                               debug=debug)
    existingFiles = [basename(each) for each in existingHashes.keys()]

    if debug is True:
        print("%d files in hashfile %s" % (len(existingFiles), hfname))

    # Calculate the new hashes by just calling the other hash logic.
    #   Big difference is that the keys are relative to the given dir, not
    #   as a full mounting path. This makes comparisons way easier.
    newKeys = {}
    newKeys = makeManifest(mdir, htype=htype, bsize=bsize,
                           filetype=filetype, forcerecheck=True,
                           fullpath=False, debug=debug)

    # Now compare the new against the old file list. Strip out path info again.
    inDR = [os.path.basename(each) for each in ff]

    # Highlight files that were in the hash file but aren't in the directory
    #   then get the filename from the hashfile but now is missing
    missing = list(set(existingFiles) - set(inDR))

    fpmissing = []
    # TODO: Clean this up with a fancy list comprehension
    for s in missing:
        for fullpathfile in existingHashes.keys():
            if s in fullpathfile:
                fpmissing.append(fullpathfile)

    mismatch = []
    nohash = []
    # Want to verify on basename basis so this can be used between machines
    #   who differ only in mount points/file structure & layout.
    #   At this point existingHashes is keyed with full paths, so repack it
    #   to be relative but still refer to the original.

    #     ff == list of files in directory
    relExisting = {}
    for it in existingHashes.items():
        relExisting.update({basename(it[0]): [it[0], it[1]]})

    for tf in ff:
        testfile = basename(tf)
        try:
            if newKeys[testfile] != relExisting[testfile][1]:
                # This means that a file in the directory failed its comparison
                #   to the value found in the hashfile.
                #   Store the full path to make retransfters easier!
                mismatch.append(tf)
        except KeyError:
            # This means that a valid file is in the directory but
            #   it doesn't have a hash in the hashfile
            nohash.append(tf)

    if debug is True:
        print({"MissingButHashed": fpmissing})
        print({"FoundButUnHashed": nohash})
        print({"FailedHashCheck": mismatch})

    return fpmissing, nohash, mismatch
