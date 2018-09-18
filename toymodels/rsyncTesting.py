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


def rsyncer(cmd, src, dest, args=None, printErrs=True, timeout=600.):
    """
    """
    if args is None:
        args = ['-arvz', '--progress']

    try:
        subcmdwargs = [cmd] + args + [src, dest]
        output = sub.run(subcmdwargs, timeout=timeout,
                         stdout=sub.PIPE, stderr=sub.PIPE)
        # Check for anything on stdout/stderr
        if output.stdout != b'':
            print((output.stdout).decode("utf-8"))

        # If the return code was non-zero, this will raise CalledProcessError
        output.check_returncode()

        # If we're here, then we're fine. Stay golden, Ponyboy
        return 0
    except sub.TimeoutExpired as err:
        if printErrs is True:
            print("Timed out!")
            print("'%s' timed out" % (" ".join(err.cmd)))

        return -99
    except sub.CalledProcessError as err:
        if printErrs is True:
            print("Command error!")
            print("'%s' returned code %d" % (" ".join(err.cmd),
                                             err.returncode))
            # We're in Python 3 territory, so err.stderr is b'' so convert
            print("Standard Error Output:")

            print((err.stderr).decode("utf-8"))

        return -999
    except FileNotFoundError as err:
        if printErrs is True:
            print("Command not found!")
            print(err.strerror)

        return -9999


def main():
    cmd = 'rsync'
    arg = ['-arvz', '--progress']
    src = './'
    timeout = 300.
    dest = '/tmp/deletable'

    retval = rsyncer(cmd, src, dest, args=arg, printErrs=True, timeout=timeout)

    if retval < 0:
        # Decision tree to act on the various failures
        if retval == -9999:
            msg = "The rsync command is incorrect and not working!"
        if retval == -999:
            msg = "The rsync command ran but encountered an error!"
        if retval == -99:
            msg = "The rsync command took longer than %d seconds!" % (timeout)
    elif retval > 0:
        msg = "Unspecified error?"
    elif retval == 0:
        msg = "Success"

    print(msg)


if __name__ == "__main__":
    main()
