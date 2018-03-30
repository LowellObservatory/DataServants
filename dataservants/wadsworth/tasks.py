# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 21 Mar 2018
#
#  @author: rhamilton

"""Tasks that Wadsworth nominally does.

These are complex actions that usually involve Yvette, in addition
to some extra processing logic to make sure things are all ok.
"""

from __future__ import division, print_function, absolute_import

import os
import datetime as dt

from .. import utils
from .. import yvette


def getFile(eSSH, remote, local):
    pass


def cleanRemote(eSSH, baseYcmd, args, iobj):
    """
    TODO: Include timeout/maxtime stuff here
    """
    # For debugging alarms
    startt = dt.datetime.utcnow()

    # Rename to control line length
    yvetteR = yvette.remote

    print("Defining custom action set for cleaning old files...")

    # Get the list of "old" files on the instrument host
    getOld = utils.common.processDescription(func=yvetteR.commandYvetteSimple,
                                             name='GetOldDirs',
                                             timedelay=3.,
                                             maxtime=60.,
                                             needSSH=True,
                                             args=[eSSH, baseYcmd, args,
                                                   iobj, 'findold'],
                                             kwargs={'debug': args.debug})

    # Define the verification function and arguments, with a quick hack first
    oiobjsrc = iobj.srcdir
    verify = utils.common.processDescription(func=yvetteR.commandYvetteSimple,
                                             name='Verify',
                                             timedelay=3.,
                                             maxtime=300.,
                                             needSSH=True,
                                             args=[eSSH, baseYcmd, args,
                                                   iobj, 'verify'],
                                             kwargs={'debug': args.debug})

    # Actually get the old dir list on Yvette's machine
    ans, _ = utils.common.instAction(getOld)

    # Now get the full directory listing on Wadsworth's machine
    ldircheck = utils.files.checkDir(iobj.destdir)
    if ldircheck is False:
        print("Destination directory unreachable! Aborting.")
        # return None

    # Type of hash file to ultimately look for
    bhfname = "AListofHashes.%s" % (args.hashtype)
    yhfname = "RemoteListofHashes.%s" % (args.hashtype)

    # Make Yvette verify these directories on her side
    #   This will make manifests in directories that don't have them
    for each in ans['DirsOld'][1]:
        # The final answer flag
        deletable = False

        # Now to start the checking process, multi-stage
        iobj.srcdir = each
        print("Getting Yvette to verify %s on %s" % (each, iobj.host))
        print(baseYcmd, getOld.args, getOld.kwargs)
        vans, estop = utils.common.instAction(verify, outertime=startt)
        print(vans)
        if estop is True:
            print("Timeout/stop reached")
            break
        # Check the status of each verification output type
        #   vans['HashChecks'] is base dict, which contains these keys:
        #     MissingFiles == Files that were hashed but now can't be found
        #     UnhashedFiles == Files found that weren't previously hashed
        #     DifferentFiles == Files that fail their hash checks
        #
        # If the last one has stuff in it, warn everyone about
        #   data shenanigans or corruption and do nothing else.
        #   Just check that it wasn't an empty result first
        if vans != {}:
            if vans['HashChecks']['DifferentFiles'] == []:
                good = True
            else:
                # TODO:
                # Possibly have Yvette re-make the file hash on her side
                #   after some sensible checks of filesize/date/time???
                good = False

            # If Yvette checks out internally, get her hash file and compare
            #   it to the local files
            if good is True:
                print("Remote checks for remote %s pass" % (each))
                # Try to YOLO it and see if the name of the remote dir exists
                #  here locally already.  Yvette's list of old dirs has NO
                #  slash on the end, so we can just basename it
                rbdir = os.path.basename(each)
                specificLocalDir = "%s/%s/" % (iobj.destdir, rbdir)
                sldircheck, sldirrp = utils.files.checkDir(specificLocalDir)
                print(specificLocalDir, sldircheck)
                if sldircheck is True:
                    # Open up our SSH file transfer pathway; if it works,
                    #   eSSH.sftp will not be None
                    eSSH.openSFTP()
                    print("Opened SFTP connection")
                    if eSSH.sftp is not None:
                        lfile = "%s/%s" % (sldirrp, yhfname)
                        rfile = "%s/%s" % (each, bhfname)
                        status = eSSH.getFile(lfile, rfile)
                        if status is True:
                            # Verify the file we just got against our local one
                            #   by comparing the hashes directly
                            print("File transfer complete")
                            print(lfile, rfile)
                            pass
                        if status is False:
                            # This means the file transfer failed for some
                            #   reason (timeout?) so move on somehow
                            print("File transfer failed!!")
                            print(lfile, rfile)
                            pass
                else:
                    # This means the directory doesn't exist locally yet,
                    #   so we'll need to transfer it over and then get it next
                    #   time for comparison.
                    pass

    # Now that we're all done with this directory:
    #   Reset the src directory to it's original value!
    #   Otherwise the next loop will fail miserably and you'll have a bad time
    iobj.srcdir = oiobjsrc
