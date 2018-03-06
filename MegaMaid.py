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
    # Base directory in which to search
    bdir = '/mnt/lemi/lois/'

    # Hacking in some arguments here
    args = '%s -o --rangeOld 25' % (bdir)
    argString = shlex.split(args)

    sys.argv += argString

    results = yvette.tidy.beginTidying(noprint=True)

    for key in results:
        print("%d directories older than 25d found" % (len(results[key])))
        for cdir in results[key]:
            print(cdir)
