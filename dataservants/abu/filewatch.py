# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 2 May 2018
#
#  @author: rhamilton

"""One line description of module.

Further description.
"""

from __future__ import division, print_function, absolute_import

import os
import sys
import time
import datetime as dt


def checkFile(fname, last, startpos):
    """
    """
    # Gather up stats about the file
    fstats = os.stat(fname)
    inode = fstats.st_ino
    fsize = fstats.st_size
    mtime = fstats.st_mtime

    print("Inode: %d" % (inode))
    print("Filesize: %d" % (fsize))
    print("ModTime: %f" % (mtime))

    # Here's the decision tree:
    read = False
    if hasattr(last, 'st_ino'):
        # If it has a different inode, it's not the same file as last time
        if inode != last.st_ino:
            print("Different file!")
            startpos = 0
            read = True
        else:
            print("Same file!")
            if fsize > last.st_size:
                print("Got bigger!")
                read = True
            elif fsize == last.st_size:
                print("Same size as last time!")
                read = False
            else:
                print("Got smaller?")
                # (think about this; could indicate copy truncation)
    else:
        print("No file to compare against!")
        read = True

    if read is True:
        with open(fname, mode='r') as f:
            f.seek(startpos)
            nlines = f.readlines()
            endpos = f.tell()
            print("Read %d lines" % (len(nlines)))

    return fstats, endpos


def whichLogDate(base):
    """
    """
    utctoday = dt.datetime.utcnow().date()
    utctomorrow = utctoday + dt.timedelta(days=1)

    # See if *tomorrow* exists, and if so use it
    exists = os.path.isfile(basename + utctomorrow)
    if exists is True:
        wfile = basename + utctomorrow.strftime("%Y%m%d")
    else:
        wfile = basename + utctoday.strftime("%Y%m%d")

    return wfile


if __name__ == "__main__":
    # Starting values
    basename = './datatests/logs/lois_log.obslemi.'
    fstats, fpos = None, 0

    while True:
        # Check for log file rollover
        wfile = whichLogDate(basename)
        fstats, fpos = checkFile(wfile, fstats, fpos)

        time.sleep(60.)
