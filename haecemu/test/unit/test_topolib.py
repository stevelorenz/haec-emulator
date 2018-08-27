#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#

import unittest

import haecemu.topolib as topolib


class testTopolib(unittest.TestCase):

    def setUp(self):
        pass

    def test_simplefattree(self):
        sft = topolib.SimpleFatTree(hosts=2)
        self.assertEqual(sft.hosts(), ['h1', 'h2'])

    def test_haeccube_fix(self):
        haec_cube = topolib.HAECCube(2, 2,
                                     intra_board_topo="mesh")
        # Check if there are duplicated links
        for link in haec_cube.links():
            if tuple(reversed(link)) in (haec_cube.links()):
                raise RuntimeError(
                    "Link {} is a duplicated link".format(link))

        haec_cube = topolib.HAECCube(3, 3,
                                     intra_board_topo="mesh")
        # Check if there are duplicated links
        for link in haec_cube.links():
            if tuple(reversed(link)) in (haec_cube.links()):
                raise RuntimeError(
                    "Link {} is a duplicated link".format(link))

        dist = haec_cube.get_node_dist("h111", "h333")
        self.assertEqual(dist, [2, 2, 2])

        hops = haec_cube.get_migrate_dst_hops("h111", "h333")
        self.assertEqual(hops, ['h332', 'h331', 'h321', 'h311', 'h211'])
        hops = haec_cube.get_migrate_dst_hops("h333", "h111")
        self.assertEqual(hops, ['h112', 'h113', 'h123', 'h133', 'h233'])

    def tearDown(self):
        pass


if __name__ == "__main__":
    unittest.main()
