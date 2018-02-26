# -*- coding: utf-8 -*-
"""
  This Source Code Form is subject to the terms of the Mozilla Public
  License, v. 2.0. If a copy of the MPL was not distributed with this
  file, You can obtain one at http://mozilla.org/MPL/2.0/.

  Created on Thu Feb 15 16:56:52 2018

  @author: rhamilton
"""

from __future__ import division, print_function, absolute_import

import os
import re
import fnmatch
from os.path import join, isdir, listdir

from . import common


def getDirListing(loc, recently=2, dirmask="[0-9]{8}.*", debug=False):
    """
    """
    # Regular expression for the format of a data directory
    #   [0-9] == any number from 0-9
    #   {8}   == match the previous set 8 times
    #   .     == any character
    # Default: "[0-9]{8}." matches 20180123a
#    regexp = re.compile(dirmask)

    # Make sure the location has an ending / to make stuff easier
    if loc[-1] != "/":
        loc += "/"

    # Need number of seconds in the day window since calendar math sucks
    recently *= 24.*60.*60.

    # Same setup as Peter's obsactive scripts now basically
    dirlist = [join(loc, x) for x in listdir(loc) if isdir(join(loc, x))]
    # At least attempt to sort it sensibly
    dirlist = sorted(dirlist)

#    if debug is True:
#        print(dirlist)

    # Need to match loc+dirmask to only catch directories ending in the
    #   regular expression (well, after the last slash)
    validdirs = [it for it in dirlist if (re.fullmatch(loc + dirmask, it))]
    if debug is True:
        print(validdirs)

    recentmod = [it for it in validdirs if common.dateDiff(it) < recently]

    if debug is True:
        if recentmod != []:
            print("Recent directories found:")
            for each in recentmod:
                print(each)
        else:
            print("No dirs matching \"%s\" found at %s" % (dirmask, loc))

#    # dirlist on remote host, with file attributes
#    dirlist = sftp.listdir_attr('.')
#
#    # Selecting only directories, which have 'd' in their permission string
#    #   it should also ignore dotfile directories
#    dirsonly = [it for it in dirlist if (it.longname[0] == 'd') and
#                                        (it.filename[0] != '.')]
#
#    # Select the directories which have been modified "recently"
#    #   where "recently" is a parameter defined elsewhere
#    now = dt.datetime.timestamp(dt.datetime.utcnow())
#    recentmod = [it for it in dirsonly if (now - it.st_mtime) < recently]
#
#    for each in recentmod:
#        print(each.longname)

    return recentmod


def recursiveSearcher(base, fileext="*.fits"):
    """
    Given a directory to start in and an optional extension to check for,
    recursively search through the directories underneath and return the
    list of files that match the fileext.
    """
    curdata = []
    for root, dirnames, filenames in os.walk(str(base)):
        for filename in fnmatch.filter(filenames, fileext):
            curdata.append(os.path.join(root, filename))

    # It'll be sorted by name, but it's better than nothing
    return sorted(curdata)


def checkDir(loc, debug=False):
    """
    Given a location, check to make sure that location actually exists
    somewhere accessible on the filesystem.
    """
    # First expand any relative paths (expanduser takes ~/ to a real place)
    fqloc = os.path.expanduser(loc)

    # Make sure the place actually exists...
    if os.path.exists(fqloc) is False:
        if debug is True:
            print("%s doesn't exist!" % (fqloc))
        return False
    else:
        return True, fqloc


def checkFreeSpace(loc, debug=False):
    """
    Given a filesystem location (/home/), return the amount of free space
    on the partition that contains that location
    """
    # First expand any relative paths (expanduser takes ~/ to a real place)
    fqloc = os.path.expanduser(loc)

    # Make sure the place actually exists...
    if checkDir(loc) is False:
        if debug is True:
            print("Fatal Error: %s doesn't exist!" % (loc))
        return None
    else:
        try:
            statvfs = os.statvfs(fqloc)
        except Exception as e:
            if debug is True:
                print("Unknown Error: %s" % (str(e)))
            return None

        if debug is True:
            print("Checking free space at %s ..." % (fqloc))

        # Check overall size, originally in bytes so /1024./1024./1024. == GiB
        total = (statvfs.f_frsize * statvfs.f_blocks)/1024./1024./1024.

        # Check free, same as above. NEED .f_bavail because
        #   .f_bfree is counting some space that's actually reserved
        free = (statvfs.f_frsize * statvfs.f_bavail)/1024./1024./1024.

        if debug is True:
            print("Total: %.2f\nFree: %.2f" % (total, free))
            print("%.0f%% remaining" % (100.*free/total))

        # Make it a bit more clear what is what via a dictionary
        retdict = {'path': None, 'total': None, 'free': None}
        retdict['path'] = loc
        retdict['total'] = total
        retdict['free'] = free

        return retdict
