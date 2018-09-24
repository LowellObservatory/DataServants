# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 18 Sep 2018
#
#  @author: rhamilton

"""One line description of module.

Further description.
"""

from __future__ import division, print_function, absolute_import

import subprocess as sub


def subpRsync(src, dest, cmd=None, args=None, timeout=600., debug=True):
    """
    rsync, called via subprocess to get at the binary on the local machine
    """
    if cmd is None:
        cmd = 'rsync'

    if args is None:
        # a: archive mode; equals -rlptgoD (no -H,-A,-X)
        # r: recurse into directories
        # m: prune empty directory chains from file-list
        # z: compress file data during the transfer
        # partial: keep partially transferred files
        # stats: give some file-transfer stats
        args = ['-armz', '--stats', '--partial']

    try:
        subcmdwargs = [cmd] + args + [src, dest]
        # NOTE: subprocess.run() is ONLY in Python >= 3.5! Could rewrite to
        #   use subprocess.Popen, but I find the subprocess.CompletedProcess
        #   instance that run() returns pretty nice.
        output = sub.run(subcmdwargs, timeout=timeout,
                         stdout=sub.PIPE, stderr=sub.PIPE)

        # Check for anything on stdout/stderr
        if debug is True:
            if output.stdout != b'':
                print((output.stdout).decode("utf-8"))

        # If the return code was non-zero, this will raise CalledProcessError
        output.check_returncode()

        gudstr = parseRsyncStats(output.stdout)

        # If we're here, then we're fine. Stay golden, Ponyboy
        return 0, gudstr
    except sub.TimeoutExpired as err:
        errstr = parseRsyncErr(err.stderr)
        if errstr is None:
            errstr = "'%s' took too long!" % (" ".join(err.cmd))
        if debug is True:
            print("Full STDERR: ", end='')
            print((err.stderr).decode("utf-8"))

        errstr = "'%s' timed out" % (" ".join(err.cmd))

        return -99, errstr
    except sub.CalledProcessError as err:
        errstr = parseRsyncErr(err.stderr)
        if errstr is None:
            errstr = "'%s' returned code %d" % (" ".join(err.cmd),
                                                err.returncode)
        if debug is True:
            print("Full STDERR: ", end='')
            print((err.stderr).decode("utf-8"))

        return -999, errstr
    except FileNotFoundError as err:
        if debug is True:
            print("rsync command not found!")
            errstr = err.strerror

        return -9999, errstr


def parseRsyncErr(errbuf):
    """
    """
    # We're in Python 3 territory, so err.stderr is a bytestring!
    if isinstance(errbuf, bytes) is True:
        errstr = errbuf.decode("utf-8")
    elif isinstance(errbuf, str) is True:
        errstr = errbuf
    else:
        errstr = None

    print(errstr)

    errsplit = errstr.split("\n")
    if errsplit[0].lower().startswith("rsync: "):
        errmsg = errsplit[0]
    else:
        errmsg = None

    return errmsg


def parseRsyncStats(outbuf):
    """
    """
    statusDict = {}

    # In theory, the rsync --stats option should output the same stuff
    #   so we'll YOLO it and search for strings to build our dict
    # We're in Python 3 territory, so err.stderr is a bytestring!
    if isinstance(outbuf, bytes) is True:
        outstr = outbuf.decode("utf-8")
    elif isinstance(outbuf, str) is True:
        outstr = outbuf
    else:
        outstr = None

    keysmap = {'Number of files:': 'nfiles',
               'Number of created files:': 'ncreated',
               'Number of deleted files:': 'ndeleted',
               'Number of regular files transferred:': 'nregxfered',
               'Total file size:': 'totsize',
               'Total transferred file size:': 'totxfersize',
               'Literal data:': 'literaldata',
               'Matched data:': 'matchdata',
               'File list size:': 'flistsize',
               'File list generation time:': 'flisttime',
               'File list transfer time:': 'flistxftertime',
               'Total bytes sent:': 'totsent',
               'Total bytes received:': 'totrecv'
               }

    if outstr is not None:
        outstr = outstr.strip()
        for key in keysmap:
            print("Searching for '%s'" % (key))
            # Since the block of stats is terminated on each line by \n,
            #   we can search the entire string block and then snip it
            #   on the *next* \n instance rather than a double loop search.
            strBeg = outstr.find(key)
            if strBeg != -1:
                strEnd = outstr.find("\n", strBeg)
                subStr = outstr[strBeg: strEnd]
                val = subStr.split(key)[1].strip()
                # Some special handling of ones with extra stuff in the line
                if keysmap[key] == 'nfiles':
                    vals = val.replace("(", "").replace(")", "").split(",")
                    nf = int(vals[0].split(":")[1])
                    nd = int(vals[1].split(":")[1])
                    val = {"nreg": nf, "ndir": nd}
                elif keysmap[key] == 'totsize' or\
                                     'totxfersize' or\
                                     'literaldata' or\
                                     'matchdata' or\
                                     'flisttime' or\
                                     'flistxftertime':
                    val = val.split()[0].strip()
                    try:
                        # Kill any commas in the numbers
                        val = val.replace(",", "")
                        val = float(val)
                    except ValueError:
                        # Just leave it as a string, then
                        pass

                print(keysmap[key], val)
                statusDict.update({keysmap[key]: val})
            print()

    return statusDict


def main():
    cmd = 'rsync'
    arg = None
    src = './'
    timeout = 300.
    dest = '/tmp/deleteme'

    retval, msg = subpRsync(src, dest, cmd=cmd, args=arg,
                            timeout=timeout, debug=True)

    print(retval, msg)


if __name__ == "__main__":
    main()
