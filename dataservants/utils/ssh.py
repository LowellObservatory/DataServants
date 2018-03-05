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


class SSHHandler():
    """
    """
    def __init__(self, host, username, password=None, port=22, timeout=30):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.timeout = timeout

    def ensureConnection(self, purpose=None):
        try:
            opener = Persistence(function=self.openConnection,
                                 errorMessage=purpose, seconds=self.timeout)
            opener.act()
            return True
        except SSHException as errtext:
            self.warning('Unable to open SSH connection:',
                         errtext, purpose)
        except socket.error as errtext:
            self.warning('Socket error connecting:',
                         errtext, purpose)
        except EOFError as errtext:
            self.warning('Server has terminated with EOFError:',
                         errtext, purpose)
        except alarms.TimeoutException as errtext:
            self.warning('Timeout error connecting:',
                         errtext)
        return False

    def openConnection(self):
        self.ssh = paramiko.SSHClient()
        self.ssh.load_system_host_keys()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(self.host, port=self.port,
                         username=self.username, password=self.password,
                         timeout=self.timeout)

    def closeConnection(self):
        self.ssh.close()

    def sendCommand(self, command, debug=False):
        """
        """
        if(self.ssh):
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
        else:
            print("SSH connection not opened!")

        return ses, stdout_data, stderr_data
