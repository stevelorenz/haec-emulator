#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#

"""
About: Util func
"""

import os
import time
from functools import wraps


def make_path_head(path):
    """Make path if not exists"""
    head, _ = os.path.split(path)
    if not os.path.exists(head):
        os.makedirs(head)


def print_time_func(p_func, fmt=None):
    """Print the execution time of a function

    :param p_func (func): Function for print
    """
    def time_func(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            t_s = time.time()
            ret = f(*args, **kwargs)
            p_func("Time it took to run func {} : {} seconds".format(
                f.__name__, time.time() - t_s
            ))
            return ret
        return wrapper
    return time_func
