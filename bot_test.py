#!/usr/bin/env python

import unittest
import bot
import email

class BotTest(unittest.TestCase):

    def setUp(self):
        self.pgp_tester = bot.OpenPGPEmailParser()
        self.emails = {
            'encrypted_to_wrong_key': email.message_from_string(open('test_emails/encrypted_to_wrong_key').read()),
            'sign': email.message_from_string(open('test_emails/signed').read())
        }

    def tearDown(self):
        pass

    def test_encrypted(self):
        props = self.pgp_tester.get_properties(self.emails['encrypted_to_wrong_key'])
        self.assertTrue(props['encrypted'])
        self.assertFalse(props['decryptable'])
        
        props = self.pgp_tester.get_properties(self.emails['signed'])
        self.assertFalse(props['encrypted'])

    def test_wrong_key(self):
        props = self.pgp_tester.get_properties(self.emails['encrypted_to_wrong_key'])
        self.assertTrue(props['encrypted'])
        self.assertFalse(props['decryptable'])

if __name__ == '__main__':
    unittest.main()

