#! /usr/bin/env python2
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#

import unittest

import mock

from haecemu.emulator import Emulator


class testEmulator(unittest.TestCase):

    def setUp(self):
        self.emu = Emulator(mode="test")

    def test_internal_funcs(self):
        pass

    def tearDown(self):
        self.emu.cleanup()


if __name__ == "__main__":
    unittest.main()
