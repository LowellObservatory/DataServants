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

from . import alarms


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
            alarms.setAlarm(handler=None, timeout=self.timeout)
            self.connect(retries=retries)
            alarms.clearAlarm()

    def connect(self, retries=5):
        """
        """
        ctries = 0
        self.success = False
        while ctries < self.retries and self.success is False:
            try:
                self.ssh.connect(self.host, port=self.port,
                                 username=self.username,
                                 password=self.password,
                                 timeout=3)
                print("SSH connection to %s opened" % (self.host))
                self.success = True
            except socket.gaierror as err:
                print("SSH connection to %s failed!" % (self.host))
                print(str(err))
                print("Retry %d" % (ctries))
                ctries += 1
                if ctries >= self.retries:
                    self.ssh = None
                else:
                    time.sleep(3)
            except Exception as err:
                # If we're here, shit got desperate
                print(str(err))
                ctries += 1
                if ctries >= self.retries:
                    self.ssh = None
                else:
                    time.sleep(3)

    def closeConnection(self, timeout=3):
        alarms.setAlarm(handler=None, timeout=timeout)
        if self.ssh is not None:
            self.ssh.close()
        alarms.clearAlarm()

    def sendCommand(self, command, timeout=10., debug=False):
        """
        """
        if(self.ssh):
            alarms.setAlarm(handler=None, timeout=timeout)
            stdin, stdout, stderr = self.ssh.exec_command(command)
            # No inputs allowed
            stdin.close()

            # Prepare the return buffers and define how many bytes at a time
            #   we'll try to digest waiting for the buffers to reach EOF
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

            if debug is True:
                print("exit status:", ses)
                print("stdout:")
                print(stdout_data)
                print("stderr:")
                print(stderr_data)

            alarms.clearAlarm()
            return ses, stdout_data, stderr_data
        else:
            print("SSH connection not opened!")
            return None, None, None


class Persistence(object):
    """
    """
    def __init__(self, function=None, seconds=30, tries=3,
                 errorMessage='Timeout'):
        self.seconds = seconds
        self.tryLimit = tries
        self.tries = 1
        self.function = function
        self.errorMessage = errorMessage

    def act(self):
        try:
            # Set the alarm via a class to be able to specify our timeout
            #   handler here rather than the default one in the util lib.
            a = alarms.alarming(self.function(), self.handleTimeout)
        except AuthenticationException as error:
            self.tryAgain(AuthenticationException(error),
                          'Authentication exception')
        finally:
            a.clearAlarm()

    def tryAgain(self, exception, message):
        if self.tries >= self.tryLimit:
            raise exception
        else:
            print(message, 'try', self.tries, self.errorMessage)
            time.sleep(2 * self.tries)
            self.tries = self.tries + 1
            self.act()
            print('Succeeded on try', self.tries)

    def handleTimeout(self, signum, frame):
        self.tryAgain(alarms.TimeoutException(self.errorMessage), 'Timed out')
