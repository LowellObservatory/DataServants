# -*- coding: utf-8 -*-
"""
  This Source Code Form is subject to the terms of the Mozilla Public
  License, v. 2.0. If a copy of the MPL was not distributed with this
  file, You can obtain one at http://mozilla.org/MPL/2.0/.

  Created on Thu Mar  1 11:19:50 2018

  @author: rhamilton
"""

from __future__ import division, print_function, absolute_import

import os
import pid
import time
import signal

from dataservants import utils

if __name__ == "__main__":
    mynameis = os.path.basename(__file__)
    if mynameis.endswith('.py'):
        mynameis = mynameis[:-3]
    kill = True
    try:
        epid = utils.pids.check_if_running(pname=mynameis)
        with pid.PidFile(pidname=mynameis, piddir='/tmp') as p:
            print(p.filename, p.pid)
            time.sleep(10000)
    except pid.PidFileError as err:
        if kill is True:
            print("Hullo!")
            print(epid)
            time.sleep(60)
            # Final line of defense, SIGTERM to PID -1 would be...bad
            #   and kill at least your login/session and other confusing things
            if epid != -1:
                os.kill(epid, signal.SIGTERM)
        else:
            print("Exists and running!!")
        print(str(err))
