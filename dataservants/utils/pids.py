# -*- coding: utf-8 -*-
"""
  This Source Code Form is subject to the terms of the Mozilla Public
  License, v. 2.0. If a copy of the MPL was not distributed with this
  file, You can obtain one at http://mozilla.org/MPL/2.0/.

  Created on Thu Feb 15 10:43:55 2018

  @author: rhamilton
"""

from __future__ import division, print_function, absolute_import


import os
import sys
import psutil
import tempfile


def nicerExit(err=None):
    """
    """
    cond = 0
    if err is not None:
        print("FATAL ERROR: %s" % (str(err)))
        cond = -1

    # Returning STDOUT and STDERR to the console/whatever
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__

    sys.exit(cond)


def check_if_running(procname='wadsworth'):
    """
    Check in the common temporary places for a wadsworth.pid file, and
    if it finds one, return the found PID (if it still exists)
    to help tell whether the script is really running or not already.

    Stale PID is defined as:
        PID in the file either doesn't exist anymore
        PID in the file doesn't have 'wadsworth' in the command line
    """

    # Most common PID file locations. Uses the tempfile module to attempt to
    #   get a cross-platform thing at least in place for the future
    #   the others are hardcoded because YOLO
    locs = ['/tmp', tempfile.gettempdir(), '~', '/var/run']
    pid = []
    found = []
    running_pid = -1
    for loc in locs:
        try:
            tfile = loc + '/' + filename
            f = open(tfile)
            # If that worked, then save the PID and the filename
            #   Saving them as lists in case multiples are found
            #   Save the filename AFTER the PID in case there's crud
            #   in the PID file other than just an int-string
            pid.append(int(f.readline()))
            found.append(tfile)
            f.close()
        except IOError:
            # Move along, this was not the file we were looking for
            pass
        except ValueError as e:
            print("Invalid data found in %s!" % (tfile))
            print(str(e))

    # If we got this far, then the at least one of those PID files
    #   both existed and had stuff in it
    if len(pid) > 0:
        for i, each in enumerate(pid):
            status = psutil.pid_exists(each)
            if status is True:
                # Important to use as_dict or oneshot to grab info immediately!
                proc = psutil.Process(each).as_dict()
                # You HAVE to search thru each element of the cmdline since
                #   the program can accept arguments and they'll be here too!
                for part in proc['cmdline']:
                    if (procname in part.lower()) is True:
                        print("%s is running! Check PID %d" % (procname, each))
                        running_pid = each
            else:
                print("Stale PID %d found; removing its PID file" % pid[i])
#                remove_pid_file(found[i])
                remove_pid_file()

    return running_pid


def write_pid_file(filename='wadsworth.pid'):
    """
    """
    # Assume a default location for now while I figure out how to
    #   pass this function arguments from the caught signals
    tloc = tempfile.gettempdir()
    cpid = os.getpid()

    ploc = tloc + "/" + filename

    try:
        f = open(ploc, 'w+')
        f.write(str(cpid))
        f.close()
        print("Wrote PID %d to file %s" % (cpid, ploc))
    except Exception as err:
        nicerExit(err)

    return cpid, ploc


def remove_pid_file(filename='/tmp/wadsworth.pid'):
    """
    """
    try:
        os.remove(filename)
    except Exception as e:
        # Not exiting on this exception since it's not a big deal if
        #  the PID file couldn't be removed; it could be that another process
        #  caused it to be deleted, and it'll be a moot point on the next run
        print("PID File Isn't There?")
        print(str(e))
