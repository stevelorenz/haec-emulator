#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#

"""
About: UDP Echo, just for func
"""

import argparse


def run_client():
    pass


def run_server():
    pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='UDP Echo')
    parser.add_argument('integers', metavar='N', type=int, nargs='+',
                        help='an integer for the accumulator')
    parser.add_argument('--sum', dest='accumulate', action='store_const',
                        const=sum, default=max,
                        help='sum the integers (default: find the max)')

    args = parser.parse_args()
