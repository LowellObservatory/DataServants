# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 20 Sep 2018
#
#  @author: rhamilton

"""One line description of module.

Further description.
"""

from __future__ import division, print_function, absolute_import

import os
import sys
import time

from dataservants import mandos
from dataservants import yvette
from dataservants import wadsworth
from ligmos.workers import workerSetup
from ligmos.utils import classes, common


def defineActions():
    """
    """
    # Renaming import to keep line length sensible
    yvetteR = yvette.remote

    # Set up the desired actions using a helpful class to pass things
    #   to each function/process more clearly.
    #
    #   Note that we need to also update things per-instrument when
    #   inside the main loop via updateArguments()...it's just helpful to
    #   do the definitions out here for the constants and for clarity.
    act1 = common.processDescription(func=yvetteR.actionSpace,
                                     name='CheckFreeSpace',
                                     timedelay=3.,
                                     maxtime=120,
                                     needSSH=True,
                                     args=[],
                                     kwargs={})

    act2 = common.processDescription(func=mandos.tasks.cleanRemote,
                                     name='CleanOldData',
                                     timedelay=3.,
                                     maxtime=600,
                                     needSSH=True,
                                     args=[],
                                     kwargs={})

    actions = [act1, act2]

    return actions


def updateArguments(actions, iobj, args, baseYcmd, db=None):
    """
    """
    # Update the functions with proper arguments.
    #   (opened SSH connection is added just before calling)
    # act1 == actionSpace
    actions[0].args = [baseYcmd, iobj]
    actions[0].kwargs = {'db': db,
                         'debug': args.debug}

    # act2 == cleanRemote
    actions[1].args = [baseYcmd, args, iobj]
    actions[1].kwargs = {}

    return actions


def main():
    """
    """
    # Define the default files we'll use/look for. These are passed to
    #   the worker constructor (toServeMan).
    # NOTE: Mandos' configuration is the *same* as Wadsworth.
    #   Mandos exists because it's easier to schedule deletion/verification
    #   as a unique task/worker and keep Wadsworth just buttling data.
    conf = './config/wadsworth.conf'
    passes = './config/passwords.conf'
    logfile = '/tmp/mandos.log'
    desc = 'Mandos: The Judge of Data'
    # Not a typo! Underscoring that Mandos and Wadsworth are connected
    eargs = wadsworth.parseargs.extraArguments
    conftype = classes.dataTarget

    # Note: We need to prepend the PATH setting here because some hosts
    #   (all recent OSes, really) have a more stringent SSHd config
    #   that disallows the setting of random environment variables
    #   at login, and I can't figure out the goddamn pty shell settings
    #   for Ubuntu (Vishnu) and OS X (xcam)
    #
    # Also need to make sure to use the relative path (~/) since OS X
    #   puts stuff in /Users/<username> rather than /home/<username>
    #   Messy but necessary due to how I'm doing SSH
    baseYcmd = 'export PATH="~/miniconda3/bin:$PATH";'
    baseYcmd += 'python ~/LIG/DataServants/Yvette.py'
    baseYcmd += ' '

    # Interval between successive runs of the instrument polling (seconds)
    bigsleep = 60

    # Total time for entire set of actions per instrument
    alarmtime = 1000

    # config: dictionary of parsed config file
    # comm: common block from config file
    # args: parsed options
    # runner: class that contains logic to quit nicely
    config, comm, args, runner = workerSetup.toServeMan(conf,
                                                        passes,
                                                        logfile,
                                                        desc=desc,
                                                        extraargs=eargs,
                                                        conftype=conftype,
                                                        logfile=True)


    # Get this PID for diagnostics
    pid = os.getpid()

    # Print the preamble of this particular instance
    #   (helpful to find starts/restarts when scanning thru logs)
    common.printPreamble(pid, config)

    # Set up the desired actions in the main loop, using a helpful class
    #   to pass things to each function/process more clearly
    #   Note that we can update things per-instrument when inside the loop
    #   it's just helpful to do the definitions out here for the constants

    # Actually define the function calls/references to functions
    print("Defining all base functions for each instrument...")
    actions = defineActions()

    # Semi-infinite loop
    while runner.halt is False:
        # This is a common core function that handles the actions and
        #   looping over each instrument.  We keep the main while
        #   loop out here, though, so we can do stuff with the
        #   results of the actions from all the instruments.
        _ = common.instLooper(config, runner, args,
                                actions, updateArguments,
                                baseYcmd,
                                db=None,
                                alarmtime=alarmtime)

        # After all the instruments are done, take a big nap
        if runner.halt is False:
            print("Starting a big sleep")
            # Sleep for bigsleep, but in small chunks to check abort
            for _ in range(bigsleep):
                time.sleep(1)
                if runner.halt is True:
                    break

    # The above loop is exited when someone sends wadsworth.py SIGTERM
    print("PID %d is now out of here!" % (pid))

    # The PID file will have already been either deleted/overwritten by
    #   another function/process by this point, so just give back the
    #   console and return STDOUT and STDERR to their system defaults
    sys.stdout = sys.__stdout__
    sys.stderr = sys.__stderr__
    print("Archive loop completed; STDOUT and STDERR reset.")


if __name__ == "__main__":
    main()
