#!/usr/bin/env python

import unittest
import bot

class BotTest(unittest.TestCase):

    def setUp(self):
        self.pgp_tester = OpenPGPEmailParser()

    def tearDown(self):
        pass

    def test_is_pgp_email(self):
        assert(True)

if __name__ == '__main__':
    unittest.main()

