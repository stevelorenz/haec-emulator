#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

"""
About: Logging
"""

import logging
import logging.handlers as handlers
from os import path

from haecemu import util

LOG_ROOT = path.join(path.expanduser("~"), ".haecemu", "log")

# Log config for dependencies
logging.getLogger("requests").setLevel(logging.WARNING)

logger = logging.getLogger('haec-emulator')


LEVELS = {
    'debug': logging.DEBUG,
    'DEBUG': logging.DEBUG,
    'info': logging.INFO,
    'INFO': logging.INFO,
    'warning': logging.WARNING,
    'WARNING': logging.WARNING,
    'error': logging.ERROR,
    'ERROR': logging.ERROR,
    'critical': logging.CRITICAL,
    'CRITICAL': logging.CRITICAL
}

FORMAT = {
    'default': '%(asctime)s [HAECEMU] %(message)s',
    'DEFAULT': '%(asctime)s [HAECEMU] %(message)s',
    'debug': '%(asctime)s %(levelname)-8s %(module)s %(threadName)s %(lineno)d [HAECEMU] %(message)s',
    'DEBUG': '%(asctime)s %(levelname)-8s %(module)s %(threadName)s %(lineno)d [HAECEMU] %(message)s',
    'info': '%(asctime)s %(levelname)-8s %(module)s [HAECEMU] %(message)s',
    'INFO': '%(asctime)s %(levelname)-8s %(module)s [HAECEMU] %(message)s'
}


def conf_logger(level, handler=None, formatter=None):
    """Config HAEC emulator root logger"""
    logger.setLevel(LEVELS[level])
    if not handler:
        handler = logging.StreamHandler()
    elif handler == "rotatingfile":
        log_file_path = path.join(LOG_ROOT, "haecemu.log")
        util.make_path_head(log_file_path)
        handler = handlers.RotatingFileHandler(
            log_file_path
        )
    if not formatter:
        formatter = logging.Formatter(FORMAT.get(level, FORMAT['default']))

    handler.setFormatter(formatter)
    logger.addHandler(handler)
