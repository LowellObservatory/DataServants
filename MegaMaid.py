# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 5 Mar 2018
#
#  @author: rhamilton
"""Mega Maid

A minimalistic batch program depending on Yvette's actions to create a
whole bunch of data manifests
"""

from __future__ import division, print_function, absolute_import

import sys
import json
import shlex

from dataservants import yvette


if __name__ == "__main__":
    # Save the original sys.argv, otherwise we'll need to always fudge arg[0]
    #   It should contain the directory desired if nothing else
    oargv = sys.argv

    # Hacking in some arguments here
    args = '-o --rangeOld 2 --oldest 365'
    argString = shlex.split(args)
    sys.argv = oargv + argString

    # Actually call Yvette to action and get the result
    results = yvette.tidy.beginTidying(noprint=True)

    for key in results:
        print("%d directories between 2 and 365d found" % (len(results[key])))
        for cdir in results[key]:
            # Prepare new arguments for Yvette. Need a dummy one to be arg[0]
            args = 'Junk! %s/ -p --filetype *.fits --hashtype xx64' % (cdir)
            args += " --debug"
            argString = shlex.split(args)
            sys.argv = argString
            results = yvette.tidy.beginTidying(noprint=True)
            print("%s: %s" % (cdir, results))
