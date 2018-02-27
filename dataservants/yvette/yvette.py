# -*- coding: utf-8 -*-
"""
  This Source Code Form is subject to the terms of the Mozilla Public
  License, v. 2.0. If a copy of the MPL was not distributed with this
  file, You can obtain one at http://mozilla.org/MPL/2.0/.

  Created on Tue Jan 30 12:53:33 2018

  @author: rhamilton
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


if __name__ == "__main__":
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
            if args.look is True:
                ddirs = utils.files.getDirListing(vdir,
                                                  dirmask=args.regexp,
                                                  recently=args.rangeNew,
                                                  debug=debug)
                rjson.update({"NewDirs": ddirs})

            # Check for optional actions
            #   NOTE: None of these are exclusionary
            if args.freespace is True:
                frees = utils.files.checkFreeSpace(args.dir, debug=debug)
                rjson.update({"FreeSpace": frees})

            if args.clean is True:
                pass

            if args.hashtype == 'xx64':
                if xxhash is None:
                    print("XX64 hash unavailable; falling back to sha1")
                    args.hashtype = 'sha1'

            if args.hashtype == 'md5':
                print("Warning: MD5 is slow! Consider another option!")

            if args.pack is True:
                # Create a manifest dict
                md1 = filehashing.makeManifest(args.dir,
                                               filetype=args.filetype,
                                               htype=args.hashtype,
                                               debug=debug)
                # Write it, and return the filename
                hfname = utils.hashes.writeHashFile(md1, args.dir,
                                                    htype=args.hashtype,
                                                    debug=debug)
                # Return logging
                rjson.update({"HashFile": hfname})

                # Now read it back in for some debug checking
                if debug is True:
                    print()
                    md2 = utils.hashes.readHashFile(hfname, debug=debug)
                    print("MD1 == MD2?\n%s" % (md1 == md2))
                    print()

                # Verification step
                broken = filehashing.verifyFiles(args.dir,
                                                 filetype=args.filetype,
                                                 htype=args.hashtype,
                                                 debug=debug)
                rjson.update({"FailedVerification": broken})
        else:
            print("%s doesn't exist or isnt' readable" % (args.dir))

    print(json.dumps(rjson))
