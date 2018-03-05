# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on Thu Feb 15 16:51:38 2018
#
#  @author: rhamilton

from __future__ import division, print_function, absolute_import

import io
import csv

from os.path import basename


try:
    # This one should always work (Python std module)
    import hashlib
    # This one might fail
    import xxhash
except ImportError:
    xxhash = None


def hashfunc(fname, bsize=2**25, htype='xx64', debug=False):
    """
    Given a filename, an optional block/chunk size to read, and a hash type,
    compute the (non-cryptographic!) hash and return it to the caller.

    blocksize (bsize) is given in bytes, so /1024 = kilobytes
    """
    if htype.lower() == 'xx64':
        if xxhash is not None:
            hasher = xxhash.xxh64()
        else:
            if debug is True:
                print("XX64 hash unavailable; falling back to sha1")
            hasher = hashlib.sha1()
    # SHA1
    elif htype.lower() == 'sha1':
        hasher = hashlib.sha1()
    # Strongly discouraged
    elif htype.lower() == 'md5':
        hasher = hashlib.md5()
    # SHA-2 family
    elif htype.lower() == 'sha256':
        hasher = hashlib.sha256()
    elif htype.lower() == 'sha512':
        hasher = hashlib.sha512()
    # SHA-3 family
    elif htype.lower() == 'sha3_256':
        hasher = hashlib.sha3_256
    elif htype.lower() == 'sha3_512':
        hasher = hashlib.sha3_512
    else:
        if debug is True:
            print("Unknown hash: %s; using sha1" % (htype))
        hasher = hashlib.sha1()

    # Actually compute the hash one chunk (of size blocksize) at a time
    #   to be gentler on memory usage for big files
    with io.open(fname, mode="rb") as fd:
        for chunk in iter(lambda: fd.read(bsize), b''):
            hasher.update(chunk)

    return hasher


def readHashFile(filename, debug=False, basenamed=False):
    """
    """
    if debug is True:
        print(filename)
    dat = {}
    try:
        with open(filename, 'r') as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                if basenamed is True:
                    cdict = {basename(row[0]): row[1]}
                else:
                    cdict = {row[0]: row[1]}
                dat.update(cdict)
    except IOError as err:
        if debug is True:
            print("%s" % (err))
        dat = {}

    return dat


def writeHashFile(mdict, loc, htype='xx64', debug=False):
    """
    """
    hfname = loc + "/AListofHashes." + htype
    try:
        with open(hfname, 'w') as csvfile:
            writer = csv.writer(csvfile)
            for item in mdict.keys():
                writer.writerow([item, mdict[item]])
        return hfname
    except IOError as err:
        if debug is True:
            print("%s" % (err))
        return None
