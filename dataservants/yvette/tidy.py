# -*- coding: utf-8 -*-
#
#   This Source Code Form is subject to the terms of the Mozilla Public
#   License, v. 2.0. If a copy of the MPL was not distributed with this
#   file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#   Created on Tue Jan 30 12:53:33 2018
#
#   @author: rhamilton

"""Yvette: The Data Maid

Yvette is designed to live locally on each target machine and remotely called
upon for work by a task using :mod:`dataservants.wadsworth`.  The remote
actions are defined in :mod:`dataservants.utils`, but the actual formatting for
the remote actions are defined in :mod:`dataservants.yvette.remote`.
"""

from __future__ import division, print_function, absolute_import

import sys
import json

try:
    # This one might fail
    import xxhash
except ImportError:
    xxhash = None

from ligmos import utils
from . import tasks
from . import parseargs
from . import filehashing


def nanny(args):
    """Take care of some common user input checks.

    Args:
        args (:class:`argparse.Namespace`)
            Class containing parsed arguments, returned from
            :func:`dataservants.yvette.parseargs.parseArguments`.

    Returns:
        dirstatus (:obj:`bool`)
            Bool indicating whether the given directory is a valid path
            on the filesystem
    """
    # A tiny bit of nanny code
    hashactions = [args.pack, args.verify, args.clean]
    if any(hashactions) is True:
        if args.hashtype == 'xx64':
            if xxhash is None:
                print("XX64 hash unavailable; falling back to sha1")
                args.hashtype = 'sha1'

        if args.hashtype == 'md5':
            print("Warning: MD5 is slow! Consider another option!")

    # Verify inputs; only do stuff if the directory is a valid one
    dirstatus, vdir = utils.files.checkDir(args.dir, debug=args.debug)

    return dirstatus, vdir


def beginTidying(noprint=False):
    """Main entry point for Yvette, which also handles arguments

    This will parse the arguments specified in
    :mod:`dataservants.yvette.parseargs` and then act
    accordingly, calling the various functions defined in
    :mod:`dataservants.utils.files` or :mod:`dataservants.utils.hashes`

    If this code is called remotely via :mod:`dataservants.wadsworth` or
    :mod:`dataservants:alfred` then the interactions are defined in
    :mod:`dataservants.yvette.remote`.

    Args:
        noprint (:obj:`bool`, optional)
            Whether to print return value to STDOUT. Defaults to False.

    Returns:
        rjson (:obj:`dict`)
            Dictionary of results from specified actions. See
            :mod:`dataservants.yvette.remote` for specifics on format.

    .. note::
        The default hash is `xx64 <https://pypi.python.org/pypi/xxhash/>`_,
        but if that is unavailable it will fall back
        to sha1. Use Yvette option ``--hashtype`` to choose a
        specific hashing function.
    """
    rjson = {}
    # Setup argument parsing *before* logging so help messages go to stdout
    #   NOTE: This function sets up the default values when given no args!
    parser, args = parseargs.setup_arguments()

    if len(sys.argv) == 1:
        parser.print_help()
    else:
        # Take care of some nanny actions
        dirstatus, vdir = nanny(args)
        if dirstatus is False:
            print("Directory %s not found or accessible!" % (vdir))

        # Setting some variables that don't depend on states/actions
        #   but might be useful to have declared for all of them
        hfname = args.dir + "/AListofHashes." + args.hashtype

        # ACTIONS start here.  If the logic is more than one or two
        #   function calls, it's been broken out into another function
        #   elsewhere
        if args.freespace is True:
            frees = utils.files.checkFreeSpace(args.dir, debug=args.debug)
            rjson.update({"FreeSpace": frees})

        if args.cpumem is True:
            cpus = utils.cpumem.checkCPUusage()
            mems = utils.cpumem.checkMemStats()
            loads = utils.cpumem.checkLoadAvgs()
            rjson.update({"MachineCPU": cpus, "MachineMem": mems,
                          "MachineLoads": loads})

        if args.checkProcess is not None:
            pstats = utils.cpumem.checkProcess(name=args.checkProcess)
            rjson.update({"ProcessStats": pstats})

        if dirstatus is True:
            # Check for non-exclusionary actions
            if args.look is True:
                ndirs = utils.files.getDirListing(vdir,
                                                  dirmask=args.regexp,
                                                  window=args.rangeNew,
                                                  comptype='newer',
                                                  debug=args.debug)
                rjson.update({"DirsNew": (len(ndirs), ndirs)})

            if args.old is True:
                odirs = utils.files.getDirListing(vdir,
                                                  dirmask=args.regexp,
                                                  window=args.rangeOld,
                                                  oldest=args.oldest,
                                                  comptype='older',
                                                  debug=args.debug)

                rjson.update({"DirsOld": (len(odirs), odirs)})

            # Check for EXCLUSIONARY actions (there can be only one)
            if args.clean is True:
                # TODO: Write the cleaning logic
                pass

            if args.pack is True:
                # Create a manifest dict
                hfname = tasks.packActions(args, hfname, debug=args.debug)
                rjson.update({"HashFile": hfname})

            if args.verify is True:
                broken = tasks.verificationActions(args, hfname,
                                                   debug=args.debug)
                if isinstance(broken, tuple):
                    rjson.update({"HashChecks": {"NFilesFound": broken[0],
                                                 "MissingFiles": broken[1],
                                                 "UnhashedFiles": broken[2],
                                                 "DifferentFiles": broken[3]}})
                else:
                    rjson.update({"HashChecks": "PROBLEMS"})

            if args.MegaMaid is True:
                res = filehashing.MegaMaid(vdir, dirmask=args.regexp,
                                           filetype=args.filetype,
                                           youngest=args.rangeOld,
                                           oldest=args.oldest,
                                           htype=args.hashtype,
                                           debug=args.debug)
                rjson.update({"MegaMaid": res})
        else:
            print("%s doesn't exist or isnt' readable" % (args.dir))

    if rjson != {} and noprint is False:
        print(json.dumps(rjson))

    return rjson
