# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 26 Mar 2018
#
#  @author: rhamilton

"""One line description of module.

Further description.
"""

from __future__ import division, print_function, absolute_import

from ligmos import utils
from . import filehashing


def cleanActions(args, hfname, debug=False):
    """
    """
    pass


def packActions(args, hfname, debug=False):
    """Logic needed to create a file of hashes in a given data directory.

    Args:
        args (:class:`argparse.Namespace`)
            Class containing parsed arguments, returned from
            :func:`dataservants.yvette.parseargs.parseArguments`.
        hfname (:obj:`str`)
            String containing the (hardcoded) hash filename.
        debug (:obj:`bool`, optional)
            Bool to trigger additional debugging outputs. Defaults to False.

    Returns:
        hfcheck (:obj:`str`)
            A string containing the full path to the created hash file. If
            the hash file could not be created, it returns the string
            "PROBLEM" indicating a problem has occured.
    """
    # Create a manifest dict
    hash1 = filehashing.makeManifest(args.dir, filetype=args.filetype,
                                     htype=args.hashtype, debug=debug)

    # If hash1 is None, then there were no files to hash
    if hash1 is not None:
        # Write it to the standard filename. If it returns not None
        #   then everything worked as intended
        hfcheck = utils.hashes.writeHashFile(hash1, hfname, debug=debug)
        # Return logging
        if hfcheck is True:
            return hfname
    else:
        return "PROBLEM"


def verificationActions(args, hfname, debug=False):
    """Logic needed to verify hashes in a given data directory.

    Args:
        args (:class:`argparse.Namespace`)
            Class containing parsed arguments, returned from
            :func:`dataservants.yvette.parseargs.parseArguments`.
        hfname (:obj:`str`)
            String containing the (hardcoded) hash filename.
        debug (:obj:`bool`, optional)
            Bool to trigger additional debugging outputs. Defaults to False.

    Returns:
        broken (:obj:`list`)
            A list of 4 elements:
                0) Number of files matching args.filetype found in directory
                1) List of files missing in the directory, but are in the
                   hash file
                2) List of files found in the directory, but are not in the
                   has file
                3) List of files existing in both the directory and the hash
                   file, but with mismatched hashes
    """
    # Verification step
    broken = filehashing.verifyFiles(args.dir, filetype=args.filetype,
                                     htype=args.hashtype, debug=debug)

    # If norepack is False and there's files to repack...then do it
    if args.norepack is False and broken[2] != []:
        hash1 = filehashing.makeManifest(args.dir, filetype=args.filetype,
                                         htype=args.hashtype, debug=debug)

        hfcheck = utils.hashes.writeHashFile(hash1, hfname, debug=debug)
        # Return logging; only try again if we wrote the file correctly
        if hfcheck is True:
            # Verify one more time to see if we got them all
            broken = filehashing.verifyFiles(args.dir, filetype=args.filetype,
                                             htype=args.hashtype, debug=debug)

    # Return the results, whatever they are. Ideally
    #   unhashed files and missing files are [] but sometimes
    #   shit happens and you don't know why so just be aware
    return broken
