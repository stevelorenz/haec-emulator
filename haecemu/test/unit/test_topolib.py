#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#

import unittest

import mock

import haecemu.topolib as topolib


class testTopolib(unittest.TestCase):

    def setUp(self):
        pass

    def test_simplefattree(self):
        sft = topolib.SimpleFatTree(hosts=2)
        self.assertEqual(sft.hosts(), ['h1', 'h2'])

    def test_haeccube_fix(self, board_len=3, board_num=3):
        haec_cube = topolib.HAECCube(board_len, board_num)
        print(haec_cube.switches())
        print(haec_cube.hosts())

    def tearDown(self):
        pass


if __name__ == "__main__":
    unittest.main()
