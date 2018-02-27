# -*- coding: utf-8 -*-
"""
Created on Fri Jan 19 12:29:01 2018

@author: rhamilton
"""

from __future__ import division, print_function, absolute_import

import io
import os
import sys
import time
import glob
import subprocess
import datetime as dt

from os.path import basename, getmtime

try:
    # This one should always work (Python std module)
    import hashlib
    # This one might fail
    import xxhash
except ImportError:
    xxhash = None


def hashfunc(fname, blocksize=2**20, hashtype='xx64'):
    """
    Given a filename, an optional block/chunk size to read, and a hash type,
    compute the (non-cryptographic!) hash and return it to the caller
    """
    if hashtype.lower() == 'xx64':
        if xxhash is not None:
            hasher = xxhash.xxh64()
        else:
            print("XX64 hash unavailable; falling back to sha1")
            hasher = hashlib.sha1()
    elif hashtype.lower() == 'sha1':
        hasher = hashlib.sha1()
    elif hashtype.lower() == 'md5':
        print("Warning: MD5 is slow! sha1 is 2-3x faster!")
        hasher = hashlib.md5()
    else:
        print("Unknown hash: %s; using sha1" % (hashtype))
        hasher = hashlib.sha1()

    # Actually compute the hash one chunk (of size blocksize) at a time
    #   to be gentler on memory usage for big files
    with io.open(fname, mode="rb") as fd:
        for chunk in iter(lambda: fd.read(blocksize), b''):
            hasher.update(chunk)

    return hasher


def mkdir(loc):
    """
    """
    # If the directory exists it'll thrown an exception, so just move on
    try:
        os.makedirs(loc)
        return loc
    except Exception as e:
        print(str(e), loc)
        return loc


def startArchiving(localloc, sofialoc, interval=30.):
    """
    Given a local location to look at, a remote location to put stuff,
    and an interval over which to check for new files, rsync the NEW
    files from local to remote.
    """

    sendc = 'rsync'
    sendb = '-arv'

    datafilenames = []
    j = 0

    while True:
        data_current = glob.glob(str(localloc) + "/*.grabme")

        # Correct the file listing to be ordered by modification time
        data_current.sort(key=getmtime)

        # Ok, lets try this beast again.
        #   Main difference here is the addition of a basename'd version
        #   of current and previous data. Maybe it's a network path bug?
        #   (grasping at any and all straws here)
        bncur = [basename(x) for x in data_current]
        bnpre = [basename(x)[:-4] + 'grabme' for x in datafilenames]

        if len(bncur) != len(bnpre):
            # Make the unique listing of old files
            s = set(bnpre)

        # Compare the new listing to the unique set of the old ones
        #   Previous logic was:
        #       diff = [x for x in self.data_current if x not in s]
        # Unrolled logic (might be easier to spot a goof-up)
        diff = []
        idxs = []
    #    print "PreviousFileList:", bnpre
    #    print "CurrentFileList:", bncur

        for i, x in enumerate(bncur):
            if x not in s:
                print("rsync'ing %s" % (x))
                idxs.append(i)
                diff.append(x)
                nammie = "%s/%s.fits" % (localloc, x[:-7])

                subprocess.call([sendc, sendb, nammie, sofialoc])

        time.sleep(interval)
        j += 1


if __name__ == "__main__":
    datalogdir = '/cygdrive/d/hawcArchive/'
    archiverdir = '/cygdrive/z/'

    now = dt.datetime.utcnow()
    nowdir = now.strftime("%Y%m%d")

    # Attempt to make the output directory AT THE START OF THE SCRIPT
    #   If the script is restarted and you cross a UT date (or don't cross it)
    #   then you could put stuff in the same directory.  Don't do that.
    archiverdir = mkdir(archiverdir + nowdir)

    # This will block until you Control+C it. It'll print out to the terminal
    #   as it archives files.
    startArchiving(datalogdir, archiverdir, interval=30.)
