# -*- coding: utf-8 -*-
"""
  This Source Code Form is subject to the terms of the Mozilla Public
  License, v. 2.0. If a copy of the MPL was not distributed with this
  file, You can obtain one at http://mozilla.org/MPL/2.0/.

  Created on Wed Jan 31 14:43:10 2018

  @author: rhamilton
"""

from __future__ import division, print_function, absolute_import

import time
import signal
import socket
import select
import datetime as dt

import paramiko
from paramiko import SSHException, AuthenticationException


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
        print("Setting alarm timer")
        signal.signal(signal.SIGALRM, self.handleTimeout)
        signal.alarm(self.seconds)
        try:
            self.function()
        except AuthenticationException as error:
            self.tryAgain(AuthenticationException(error),
                          'Authentication exception')
        finally:
            print("Removing alarm timer")
            signal.alarm(0)

    def tryAgain(self, exception, message):
        if self.tries >= self.tryLimit:
            raise exception
        else:
            print(message, 'try', self.tries, self.errorMessage)
            time.sleep(2*self.tries)
            self.tries = self.tries + 1
            self.act()
            print('Succeeded on try', self.tries)

    def handleTimeout(self, signum, frame):
        self.tryAgain(TimeoutError(self.errorMessage), 'Timed out')


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
        except TimeoutError as errtext:
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

    def sendCommand(self, command, env=None):
        if(self.ssh):
            if env is None:
                stdin, stdout, stderr = self.ssh.exec_command(command,
                                                              get_pty=True)
            else:
                stdin, stdout, stderr = self.ssh.exec_command(command,
                                                              get_pty=True,
                                                              environment=env)
            while not stdout.channel.exit_status_ready():
                # Print data when available
                if stdout.channel.recv_ready():
                    rl, wl, xl = select.select([stdout.channel], [], [], 0.0)
                    if len(rl) > 0:
                        # Print data from stdout
                        print(stdout.channel.recv(1024),)
#                if stdout.channel.recv_ready():
#                    alldata = stdout.channel.recv(1024)
#                    prevdata = b"1"
#                    while prevdata:
#                        prevdata = stdout.channel.recv(1024)
#                        alldata += prevdata
#                    print(str(alldata, "utf8"))
        else:
            print("SSH connection not opened!")

        return


class TimeoutError(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


def nicerSSHCommand(host, port, username, cmdwargs,
                    password=None, timeout=30):
    """
    """
    # The class has 3 retries baked into it for the initial connection
    eSSH = SSHHandler(host, username, password=password, port=port)
    eSSH.ensureConnection()

    print("running remote python command: '%s'" % (cmdwargs))

    try:
        eSSH.sendCommand(cmdwargs)
    except socket.timeout as error:
        print("Socket timeout:")
        print("'%s' didn't return for %d seconds" % (cmdwargs, timeout))
        print(str(error))

    eSSH.closeConnection()
    print("closed connection")
