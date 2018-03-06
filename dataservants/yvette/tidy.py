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


def beginTidying():
    """Main entry point for Yvette, which also handles arguments

    This will parse the arguments specified in
    :mod:`dataservants.yvette.parseargs` and then act
    accordingly, calling the various functions defined in
    :mod:`dataservants.utils.files` or :mod:`dataservants.utils.hashes`

    Args:
        None

    Returns:
        None

    While this function returns nothing, it prints the results of the actions
    to STDOUT in a JSON format, to be unpacked by whichever function (remotely)
    called Yvette.
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
        if dirstatus is True:
            # Check for non-exclusionary actions
            if args.look is True:
                ndirs = utils.files.getDirListing(vdir,
                                                  dirmask=args.regexp,
                                                  window=args.rangeNew,
                                                  comptype='newer',
                                                  debug=debug)
                rjson.update({"DirsNew": ndirs})

            if args.freespace is True:
                frees = utils.files.checkFreeSpace(args.dir, debug=debug)
                rjson.update({"FreeSpace": frees})

            if args.old is True:
                odirs = utils.files.getDirListing(vdir,
                                                  dirmask=args.regexp,
                                                  window=args.rangeOld,
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
                # Write it to the standard filename. If it returns not None
                #   then everything worked as intended
                hfname = args.dir + "/AListofHashes." + args.hashtype
                hfname = utils.hashes.writeHashFile(hash1, hfname,
                                                    debug=debug)

                # Return logging
                rjson.update({"HashFile": hfname})

                # Now read it back in for some debug checking
                if debug is True:
                    print()
                    hash2 = utils.hashes.readHashFile(hfname, debug=debug)
                    print("hashset1 == hashset2?\n%s" % (hash1 == hash2))
                    print()

            if args.verify is True:
                # Verification step
                broken = filehashing.verifyFiles(args.dir, args.verify,
                                                 filetype=args.filetype,
                                                 htype=args.hashtype,
                                                 debug=debug)
                rjson.update({"FailedHashVerifications": broken})
        else:
            print("%s doesn't exist or isnt' readable" % (args.dir))

    if rjson != {}:
        print(json.dumps(rjson))
