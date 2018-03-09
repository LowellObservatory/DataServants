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

from .. import utils
from . import parseargs
from . import filehashing


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
        if args.debug is True:
            debug = True
        else:
            debug = False

        # Verify inputs; only do stuff if the directory is a valid one
        dirstatus, vdir = utils.files.checkDir(args.dir, debug=debug)
        if dirstatus is False:
            print("Directory %s not found or accessible!" % (vdir))
            sys.exit(-1)

        # Setting some variables that don't depend on states/actions
        #   but might be useful to have declared for all of them
        hfname = args.dir + "/AListofHashes." + args.hashtype

        #
        # ACTIONS
        #
        if args.freespace is True:
                frees = utils.files.checkFreeSpace(args.dir, debug=debug)
                rjson.update({"FreeSpace": frees})

        if args.cpumem is True:
            loads = utils.cpumem.checkCPUusage()
            mems = utils.cpumem.checkMemStats()
            rjson.update({"MachineCPU": loads, "MachineMem": mems})

        if dirstatus is True:
            # Check for non-exclusionary actions
            if args.look is True:
                ndirs = utils.files.getDirListing(vdir,
                                                  dirmask=args.regexp,
                                                  window=args.rangeNew,
                                                  comptype='newer',
                                                  debug=debug)
                rjson.update({"DirsNew": ndirs})

            if args.old is True:
                odirs = utils.files.getDirListing(vdir,
                                                  dirmask=args.regexp,
                                                  window=args.rangeOld,
                                                  oldest=args.oldest,
                                                  comptype='older',
                                                  debug=debug)

                rjson.update({"DirsOld": odirs})

            # A tiny bit of nanny code
            hashactions = [args.pack, args.verify, args.clean]
            if any(hashactions) is True:
                if args.hashtype == 'xx64':
                    if xxhash is None:
                        print("XX64 hash unavailable; falling back to sha1")
                        args.hashtype = 'sha1'

                if args.hashtype == 'md5':
                    print("Warning: MD5 is slow! Consider another option!")

            # Check for EXCLUSIONARY actions (there can be only one)
            if args.clean is True:
                # TODO: Write the cleaning logic
                pass

            if args.pack is True:
                # Create a manifest dict
                hash1 = filehashing.makeManifest(args.dir,
                                                 filetype=args.filetype,
                                                 htype=args.hashtype,
                                                 debug=debug)
                # If hash1 is None, then there were no files to hash
                if hash1 is not None:
                    # Write it to the standard filename. If it returns not None
                    #   then everything worked as intended
                    hfcheck = utils.hashes.writeHashFile(hash1, hfname,
                                                         debug=debug)

                    # Return logging
                    if hfcheck is True:
                        rjson.update({"HashFile": hfname})
                    else:
                        rjson.update({"HashFile": "PROBLEM"})

                # Now read it back in for some debug checking
                if debug is True:
                    print()
                    hash2 = utils.hashes.readHashFile(hfname, debug=debug)
                    print("hashset1 == hashset2?\n%s" % (hash1 == hash2))
                    print()

            if args.verify is True:
                # Verification step
                broken = filehashing.verifyFiles(args.dir,
                                                 filetype=args.filetype,
                                                 htype=args.hashtype,
                                                 debug=debug)

                # If norepack is False and there's files to repack...then do it
                if args.norepack is False and broken[1] != []:
                    hash1 = filehashing.makeManifest(args.dir,
                                                     filetype=args.filetype,
                                                     htype=args.hashtype,
                                                     debug=debug)
                    hfname = args.dir + "/AListofHashes." + args.hashtype
                    hfcheck = utils.hashes.writeHashFile(hash1, hfname,
                                                         debug=debug)

                    # Verify one more time to see if we got them all
                    broken = filehashing.verifyFiles(args.dir,
                                                     filetype=args.filetype,
                                                     htype=args.hashtype,
                                                     debug=debug)

                # Return the results, whatever they are. Ideally
                #   unhashed files and missing files are [] but sometimes
                #   shit happens and you don't know why so just be aware
                rjson.update({"HashChecks": {"MissingFiles": broken[0],
                                             "UnhashedFiles": broken[1],
                                             "DifferentFiles": broken[2]}})
        else:
            print("%s doesn't exist or isnt' readable" % (args.dir))

    if rjson != {} and noprint is False:
        print(json.dumps(rjson))

    return rjson
