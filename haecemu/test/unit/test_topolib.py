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

    def test_haeccube_fix(self):
        for board_len, board_num in (
                (2, 2),
                (3, 3),
        ):
            haec_cube = topolib.HAECCube(board_len, board_num,
                                         intra_board_topo="mesh")
            print(sorted(haec_cube.nodes()))
            print(sorted(haec_cube.links()))

            # Check if there are duplicated links
            valid_links = list()
            for link in haec_cube.links():
                if tuple(reversed(link)) in (haec_cube.links()):
                    raise RuntimeError(
                        "Link {} is a duplicated link".format(link))

        print(haec_cube.get_link_energy_cost("h111", "h222"))
        print(haec_cube.get_link_energy_cost("h111", "h121"))

    def tearDown(self):
        pass


if __name__ == "__main__":
    unittest.main()
