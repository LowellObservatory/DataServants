# -*- coding: utf-8 -*-
"""
  This Source Code Form is subject to the terms of the Mozilla Public
  License, v. 2.0. If a copy of the MPL was not distributed with this
  file, You can obtain one at http://mozilla.org/MPL/2.0/.

  Created on Thu Feb 15 10:43:55 2018

  @author: rhamilton
"""

from __future__ import division, print_function, absolute_import


#import os
#import sys
import psutil
import tempfile


def check_if_running(pname='wadsworth', debug=False):
    """
    Check in the common temporary places for a wadsworth.pid file, and
    if it finds one, return the found PID (if it still exists)
    to help tell whether the script is really running or not already.

    Assumes that the PID filename is of the form procname + '.pid'
    """
    # Most common PID file locations. Uses the tempfile module to attempt to
    #   get a cross-platform thing at least in place for the future
    #   the others are hardcoded because YOLO
    locs = ['/tmp', tempfile.gettempdir(), '~', '/var/run']
    # Quick cludge for OS X keeping its tempdir as private but linux as public
    locs = set(locs)
    pid = []
    found = []
    running_pid = -1
    for loc in locs:
        try:
            tfile = loc + '/' + pname.lower() + '.pid'
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
                # Sentinel value
                running_pid = 1
                # Important to use as_dict/ oneshot to grab info!
                proc = psutil.Process(each).as_dict()
                if debug is True:
                    print(proc)
                # Check to see if the process name is on the cmdline first
                # You HAVE to search thru each element of the cmdline since
                #   the program can accept arguments and they'll be here too!
                for part in proc['cmdline']:
                    if (pname.lower() in part.lower()) is True:
                        print("%s is running! Check PID %d" % (pname, each))
                        running_pid = each
                if running_pid == -1:
                    # If that didn't work...
                    # Now check the open files to see if one of them is
                    #   the procname; could happen with debuggers
                    for ofile in proc['open_files']:
                        # Make sure we're not just seeing the open PID file
                        #   running process, otherwise we'll get confused
                        if debug is True:
                            print(ofile.path)
                        if ofile.path != found[i]:
                            if (pname in ofile.path.lower()) is True:
                                print("%s is running! Check PID %d" % (pname,
                                                                       each))
                                running_pid = each
            else:
                print("Stale PID %d found, PidFile manager will deal with it" %
                      (pid[i]))
#                remove_pid_file(pid[i])

    return running_pid
