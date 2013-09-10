#!/usr/bin/env python

import unittest
import bot
import email

class BotTest(unittest.TestCase):

    def setUp(self):
        self.pgp_tester = bot.OpenPGPEmailParser()
        self.emails = {
            'encrypted_to_wrong_key': email.message_from_string(open('test_emails/encrypted_to_wrong_key').read()),
            'signed': email.message_from_string(open('test_emails/signed').read()),
            'unencrypted_thunderbird': email.message_from_string(open('test_emails/unencrypted_thunderbird').read())
        }

    def tearDown(self):
        pass

    def test_encrypted(self):
        self.pgp_tester.set_new_email(self.emails['encrypted_to_wrong_key'])
        self.pgp_tester.is_pgp_email()
        self.assertTrue(self.pgp_tester.properties['encrypted'])

    def test_unencrypted(self):
        self.pgp_tester.set_new_email(self.emails['unencrypted_thunderbird'])
        self.pgp_tester.is_pgp_email()
        self.assertFalse(self.pgp_tester.properties['encrypted'])

    def test_signed(self):
        self.pgp_tester.set_new_email(self.emails['signed'])
        self.pgp_tester.is_pgp_email()
        self.assertTrue(self.pgp_tester.properties['signed'])
        
    def test_unsigned(self):
        self.pgp_tester.set_new_email(self.emails['signed'])
        self.pgp_tester.is_pgp_email()
        self.assertTrue(self.pgp_tester.properties['signed'])

    def test_wrong_key(self):
        # tododta this needs test key
        pass


if __name__ == '__main__':
    unittest.main()
