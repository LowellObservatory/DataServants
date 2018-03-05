# -*- coding: utf-8 -*-
#
#  This Source Code Form is subject to the terms of the Mozilla Public
#  License, v. 2.0. If a copy of the MPL was not distributed with this
#  file, You can obtain one at http://mozilla.org/MPL/2.0/.
#
#  Created on Thu Feb 15 11:01:52 2018
#
#  @author: rhamilton

from __future__ import division, print_function, absolute_import

import sys
import logging
import logging.handlers


class MyLogger(object):
    """
    The logger is a class so we can use it to capture stdout + sterr in the log
    """
    def __init__(self, logger, level):
        """Always needs a logger and a logger level."""
        self.logger = logger
        self.level = level

    def write(self, message):
        # Only log if there is a message (not just a new line)
        if message.rstrip() != "":
            self.logger.log(self.level, message.rstrip())

    def flush(self):
        """
        Need this noop to be happy in a threaded/multiprocessing world
        """
        pass


def setup_logging(logName='/tmp/wadsworth.log', nLogs=30):
    """
    A place for the mundane setup tasks to clear up __main__ or whatever
    main loop is decided upon

    Takes some option arguments:
        LOG_FILENAME: Fully qualified path of log filename to write to
        nLogs: Number of logs to keep in reserve

    The logs are (currently) specified to rotate at the time given in
    'TimedRotationFileHandler' via the 'utc' and 'when' arguments.
    """
    # The below could also be "DEBUG" or "WARNING"
    LOG_LEVEL = logging.INFO

    # Configure logging to log to a file, making a new file at midnight and
    #  keeping the last 3 day's data.
    logger = logging.getLogger(__name__)
    # Set the log level to LOG_LEVEL
    logger.setLevel(LOG_LEVEL)
    # Make a handler that writes to a file, making a new file at midnight
    #  and keeping X backups

    # For the DCT, midnight UTC is ~5 PM local time
    handler = logging.handlers.TimedRotatingFileHandler(logName,
                                                        when="midnight",
                                                        utc=True,
                                                        backupCount=nLogs)
    # Format each log message like this
    formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
    # Attach the formatter to the handler
    handler.setFormatter(formatter)
    # Attach the handler to the logger
    logger.addHandler(handler)

    print("NOTE: Henceforth, STDOUT and STDERR are redirected to %s" %
          (logName))

    # Replace stdout with logging to file at INFO level
    sys.stdout = MyLogger(logger, logging.INFO)
    # Replace stderr with logging to file at ERROR level
    sys.stderr = MyLogger(logger, logging.ERROR)
