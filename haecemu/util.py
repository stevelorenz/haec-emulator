#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#

"""
About: Util func
"""

import os


def make_path_head(path):
    """Make path if not exists"""
    head, _ = os.path.split(path)
    if not os.path.exists(head):
        os.makedirs(head)
