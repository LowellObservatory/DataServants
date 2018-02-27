# -*- coding: utf-8 -*-
"""
  This Source Code Form is subject to the terms of the Mozilla Public
  License, v. 2.0. If a copy of the MPL was not distributed with this
  file, You can obtain one at http://mozilla.org/MPL/2.0/.

  Created on Tue Feb 27 12:46:30 2018

  @author: rhamilton
"""

from __future__ import division, print_function, absolute_import

from collections import OrderedDict

try:
    import configparser as conf
except ImportError:
    import ConfigParser as conf

from . import common


def parseInstConf(filename, debug=False, parseHardFail=True):
    """
    Parse the .conf file that gives the setup per instrument
    Returns an ordered dict of Instrument classes that the conf file
    has 'enabled=True'
    """
    try:
        config = conf.SafeConfigParser()
        config.read_file(open(filename, 'r'))
    except IOError as err:
        common.nicerExit(err)

    print("Found the following instruments in the configuration file:")
    sections = config.sections()
    tsections = ' '.join(sections)
    print("%s\n" % tsections)

    print("Attempting to assign the configuration parameters...")
    inlist = []
    for each in sections:
        print("Applying '%s' section of conf. file..." % (each))
        inlist.append(common.InstrumentHost(conf=config[each],
                                            parseHardFail=parseHardFail))

    # Making a dict of *just* the active instruments
    idict = OrderedDict()
    for inst in inlist:
        if inst.enabled is True:
            idict.update({inst.name: inst})

    return idict


def parsePassConf(filename, idict, debug=False):
    """
    Parse the .conf file that gives the passwords per user.

    Returns an ordered dict of results, that then need to be associated with
    the idict returned from parseInstConf.
    """
    try:
        config = conf.SafeConfigParser()
        config.read_file(open(filename, 'r'))
    except IOError as err:
        common.nicerExit(err)

    print("Found the following usernames in the password file:")
    sections = config.sections()
    tsections = ' '.join(sections)
    print("%s\n" % tsections)

    for each in idict.keys():
        # Get the username for this instrument
        iuser = idict[each].user
        # Now see if we have a password for this username
        try:
            passw = config[iuser]['pw']
        except KeyError:
            if debug is True:
                print("Username %s has no password!" % (iuser))
            passw = None

        if debug is True:
            print(iuser, passw)
        idict[each].addPass(passw)

    return idict
