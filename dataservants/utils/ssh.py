# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on Wed Jan 31 14:43:10 2018
#
#  @author: rhamilton

from __future__ import division, print_function, absolute_import

import time
import socket

import paramiko
from paramiko import SSHException, AuthenticationException

from . import multialarm


class SSHWrapper():
    """
    """
    def __init__(self, host='', username='',
                 port=22, password='', retries=5, timeout=30.,
                 connectOnInit=True):
        self.host = host
        self.username = username
        self.port = port
        self.password = password
        self.retries = retries
        self.timeout = timeout

        # Paramiko stuff
        self.ssh = paramiko.SSHClient()
        self.ssh.load_system_host_keys()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        if connectOnInit is True:
            self.connect(retries=retries, maxtime=self.timeout)

    def connect(self, retries=5, maxtime=60):
        """
        """
        # Hardcoded wait/timeout of 10 seconds for SSH connection
        #   BUT, that timeout is pretty janky and doesn't always
        #   work or even timeout properly so that's why we have
        #   a multialarm.Timeout wrapper on everything here below
        sshitimeout = 5

        # Counter and flag related to retries
        ctries = 0
        self.success = False

        try:
            # Set a timer for the whole connect/retry process
            with multialarm.Timeout(id_="SSHConnTotal", seconds=maxtime):
                while ctries < self.retries and self.success is False:
                    try:
                        self.ssh.connect(self.host, port=self.port,
                                         username=self.username,
                                         password=self.password,
                                         timeout=sshitimeout,
                                         banner_timeout=sshitimeout,
                                         auth_timeout=sshitimeout)
                        print("SSH connection to %s opened" % (self.host))
                        self.success = True
                    except socket.error as err:
                        # Using base socket class to try to catch all the
                        #   bad stuff that could go wrong...
                        #   paramiko documentation kinda sucks here.
                        print("SSH connection to %s failed!" % (self.host))
                        print(str(err))
                        print("Retry %d" % (ctries))
                        ctries += 1
                        if ctries >= self.retries:
                            self.ssh = None
                        else:
                            time.sleep(3)
        except multialarm.TimeoutError as err:
            # Only deal with our specific SSH timeout error
            if err.id_ == "SSHConnTotal":
                print(str(err))
                ctries += 1
                if ctries >= self.retries:
                    self.ssh = None
                else:
                    time.sleep(3)

    def closeConnection(self, timeout=3):
        try:
            with multialarm.Timeout(id_="SSHClose", seconds=timeout):
                if self.ssh is not None:
                    self.ssh.close()
        except multialarm.TimeoutError as err:
            if err.id_ == "SSHClose":
                self.ssh = None
                print("SSH connection close failed? WTF?")

    def sendCommand(self, command, timeout=10., debug=False):
        """
        """
        # Use this to directly print out stdout/stderr
        superdebug = False

        ses, stdout_data, stderr_data = None, None, None
        if(self.ssh):
            try:
                with multialarm.Timeout(id_="SSHCmd", seconds=timeout):
                    stdin, stdout, stderr = self.ssh.exec_command(command)
                    # No inputs allowed
                    stdin.close()

                    # Prepare the return buffers and define how many bytes
                    #   at a time we'll try to digest waiting for the
                    #   buffers to reach EOF
                    stdout_data = []
                    stderr_data = []
                    nbytes = 1024.

                    while not stdout.channel.exit_status_ready():
                        ans = stdout.channel.recv(nbytes)
                        stdout_data.append(str(ans, "utf8"))

                    # Get the exit status
                    ses = stdout.channel.exit_status
                    # Collapse into just a string
                    stdout_data = "".join(stdout_data)

                    while not stderr.channel.exit_status_ready():
                        err = stderr.channel.recv_stderr(nbytes)
                        stderr_data.append(str(err, "utf8"))
                    stderr_data = "".join(stderr_data)

                    if superdebug is True:
                        print("exit status:", ses)
                        print("stdout:")
                        print(stdout_data)
                        print("stderr:")
                        print(stderr_data)
            except multialarm.TimeoutError as err:
                if err.id_ == "SSHCmd":
                    print("SSH Command Timed Out!")
                    print(err)
        else:
            print("SSH connection not opened!")
            print("Trying to open it one more time...")
            # Open once more

        return ses, stdout_data, stderr_data
