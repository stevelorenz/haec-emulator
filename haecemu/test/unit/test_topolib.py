#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8
#

import unittest

import haecemu.topolib as topolib


class testTopolib(unittest.TestCase):

    def setUp(self):
        pass

    def test_staticperfectfattree(self):

        with self.assertRaisesRegexp(topolib.TopolibError,
                                     "StaticPerfectFatTree supports only perfect tree."):
            sft = topolib.StaticPerfectFatTree(hosts=3)

        sft = topolib.StaticPerfectFatTree(hosts=8)

        self.assertEqual(sft._get_lca("s1", "s2"), "s9")
        self.assertEqual(sft._get_lca("s1", "s4"), "s13")
        self.assertEqual(sft._get_lca("s1", "s5"), "s15")
        self.assertEqual(sft.get_node_dist("h1", "h2"), 2)
        self.assertEqual(sft.get_node_dist("h1", "h4"), 4)
        self.assertEqual(sft.get_node_dist("h1", "h5"), 6)

        sft = topolib.StaticPerfectFatTree(hosts=2)
        self.assertEqual(sft.hosts(), ['h1', 'h2'])

    def test_haeccub(self):
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
