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

from ligmos import utils
from .. import yvette


def buttleData(eSSH, baseYcmd, args, iobj):
    """
    """
    # For debugging alarms
    startt = dt.datetime.utcnow()

    # Rename to control line length
    yR = yvette.remote
    yH = yvette.filehashing
    uH = utils.hashes

    # Need to make sure our destination directory actually exists first
    ldircheck = utils.files.checkDir(iobj.destdir)
    if ldircheck[0] is False:
        print("--> Local destination directory unreachable! Aborting!")
        # return None

    print("--> Defining custom action set for buttling files...")

    # Get the list of "old" files on the instrument host
    getNew = utils.common.processDescription(func=yR.commandYvetteSimple,
                                             name='GetNewDirs',
                                             timedelay=3.,
                                             maxtime=60.,
                                             needSSH=True,
                                             args=[eSSH, baseYcmd, args,
                                                   iobj, 'findnew'],
                                             kwargs={'debug': args.debug})

    verify = utils.common.processDescription(func=yR.commandYvetteSimple,
                                             name='Verify',
                                             timedelay=3.,
                                             maxtime=625.,
                                             needSSH=True,
                                             args=[eSSH, baseYcmd, args,
                                                   iobj, 'verify'],
                                             kwargs={'debug': args.debug})

    # Actually get the dir list on Yvette's machine
    ans, _ = utils.common.instAction(getNew)

    # rsync each directory, one by one so we can gather the stats
    for each in ans['DirsNew'][1]:
        # Now to start the checking process, multi-stage
        print("--> rsyncing remote %s:%s to local %s" % (iobj.host,
                                                         each, iobj.destdir))

        rsyncsrc = "%s@%s:%s" % (iobj.user, iobj.host, each)
        print(rsyncsrc)
        ret = utils.rsyncer.subpRsync(rsyncsrc, iobj.destdir, timeout=0)
        print(ret)
