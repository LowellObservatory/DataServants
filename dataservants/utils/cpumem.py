# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on 6 Mar 2018
#
#  @author: rhamilton

from __future__ import division, print_function, absolute_import

import os
import psutil
import datetime as dt


def find_procs_by_name(name,
                       ignore=['yvette.py', 'alfred.py', 'wadsworth.py']):
    """
    Return a list of processes matching 'name'.

    Ignores processes with ignore in them to keep it from finding the
    searching process, which would be silly.
    """
    ls = []
    for p in psutil.process_iter(attrs=["name", "exe", "cmdline"]):
        skip = False
        try:
            _name = p.info['name']
            cmd = p.info['cmdline']
            exe = _name = p.info['exe']
            exe = p.exe()
        except (psutil.AccessDenied, psutil.ZombieProcess):
            skip = True
            pass
        except psutil.NoSuchProcess:
            skip = True
            continue

        if cmd is None:
            skip = True

        if skip is False:
            # Layer 1 check
            chk = False
            chk = name in [os.path.basename(each) for each in cmd]

            # Layer 2 checks
            chk2 = False
            for ig in ignore:
                chk2 = ig in [os.path.basename(each.lower()) for each in cmd]
                if chk2 is True:
                    chk = False

            if name == _name or\
               chk is True or\
               os.path.basename(exe) == name:
                ls.append(p)
    return ls


def checkProcess(name='lois'):
    """
    """
    fpdict = {}
    piddict = {}

    boottime = psutil.boot_time()
    host = os.uname()[1]
    fpdict.update({'boottime': boottime})
    fpdict.update({'hostname': host})

    # Check to see if the name is [N,n]one indicating we really didn't want
    #   to search for anything. Can't depend on NoneType since it could
    #   be a remote request from Wadsworth or Alfred.
    if name.lower() == 'none':
        name = None

    tsu = dt.datetime.utcnow().timestamp()

    if name is not None:
        fprocs = find_procs_by_name(name)
        for p in fprocs:
            # Make sure this process still is what we think and it didn't die
            #   by the time we get down here to check on stuff.
            if p.is_running() is True:
                pd = p.as_dict()
                rd = {'cmdline': pd['cmdline'],
                      'createtime': pd['create_time'],
                      'age': tsu - pd['create_time'],
                      'exe': pd['exe'],
                      'name': pd['name'],
                      'num_fds': pd['num_fds'],
                      'num_threads': pd['num_threads'],
                      'pid': pd['pid'],
                      'ppid': pd['ppid'],
                      'status': pd['status'],
                      'terminal': pd['terminal'],
                      'username': pd['username']}
                piddict.update({p.pid: rd})
        if piddict == {}:
            # This means we didn't find anything, but tried, so panic
            piddict = {"ProcessNotFound": True}
    else:
        # If we didn't give a name, then we couldn't have failed. Perfection.
        piddict = None

    fpdict.update({"PIDS": piddict})

    return fpdict


def checkLoadAvgs():
    """
    """
    res = os.getloadavg()
    ans = {'Avg1Min': res[0],
           'Avg5Min': res[1],
           'Avg15Min': res[2]}

    return ans


def checkCPUusage():
    """
    """
    # NOTE: interval MUST be > 0.1s otherwise it'll give garbage results
    res = psutil.cpu_times_percent(interval=1.0)

    # At this point res is a namedtuple type, so we need to dance a little bit
    #   (_asdict() is a builtin method and _fields is a builtin property)
    ans = {}
    rd = res._asdict()
    for each in res._fields:
        ans.update({each: rd[each]})

    return ans


def checkMemStats():
    """
    """
    res = psutil.virtual_memory()

    # See above; same dance routine
    ans = {}
    rd = res._asdict()
    for each in res._fields:
        # Just go ahead and put the values from bytes to GiB
        ans.update({each: rd[each]/1024./1024./1024.})

    # One last one to help plotting
    ans.update({"percent": ans["available"]/ans["total"]})

    return ans
