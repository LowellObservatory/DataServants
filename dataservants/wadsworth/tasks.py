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

from .. import utils
from .. import yvette


def getFile(eSSH, remote, local):
    pass


def cleanRemote(eSSH, baseYcmd, args, iobj, lpath):
    """
    """
    # Rename to control line length
    yvetteR = yvette.remote

    # Get the list of "old" files
    getOld = utils.common.processDescription(func=yvetteR.commandYvetteSimple,
                                             timedelay=3.,
                                             maxtime=120,
                                             needSSH=True,
                                             args=[baseYcmd, args,
                                                   iobj, 'findold'],
                                             kwargs={'debug': args.debug})
    # Actually call the function
    ans, _ = utils.common.instAction(getOld)

    # Define the verification function and arguments, with a quick hack first
    oiobjsrc = iobj.srcdir
    verify = utils.common.processDescription(func=yvetteR.commandYvetteSimple,
                                             timedelay=3.,
                                             maxtime=120,
                                             needSSH=True,
                                             args=[baseYcmd, args,
                                                   iobj, 'verify'],
                                             kwargs={'debug': args.debug})

    # Make Yvette verify these directories on her side
    for each in ans:
        iobj.srcdir = each
        vans, _ = utils.common.instAction(verify)
        print(vans)
