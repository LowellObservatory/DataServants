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

    # Get the list of "old" files
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

    # Actually get the old dir list
    print(getOld.__dict__)
    print(iobj.__dict__)
    ans, _ = utils.common.instAction(getOld)
    print(ans)

    # Make Yvette verify these directories on her side
    #   This will make manifests in directories that don't have them,
    #   as well as
    for each in ans['DirsOld'][1]:
        iobj.srcdir = each
        print("Getting Yvette to verify %s on %s" % (each, iobj.host))
        vans, estop = utils.common.instAction(verify, outertime=startt)
        print(vans)
        if estop is True:
            print("Timeout/stop reached")
            break

    # Reset the src directory to it's original value! Otherwise the next loop
    #   will fail miserably and you'll have a bad time
    iobj.srcdir = oiobjsrc
