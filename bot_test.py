#!/usr/bin/env python

import unittest
import bot
import email

class BotTest(unittest.TestCase):

    def setUp(self):
        self.pgp_tester = bot.OpenPGPEmailParser()

        self.emails = {}
        for filename in ['encrypted_to_wrong_key', 'signed', 'unencrypted_thunderbird']:
            self.emails[filename] = email.message_from_string(open('test_emails/'+filename).read())

    def tearDown(self):
        pass

    def test_encrypted(self):
        self.pgp_tester.set_new_email(self.emails['encrypted_to_wrong_key'])
        self.assertTrue(self.pgp_tester.properties['encrypted'])

    def test_unencrypted(self):
        self.pgp_tester.set_new_email(self.emails['unencrypted_thunderbird'])
        self.assertFalse(self.pgp_tester.properties['encrypted'])

    def test_signed(self):
        self.pgp_tester.set_new_email(self.emails['signed'])
        self.assertTrue(self.pgp_tester.properties['signed'])
        
    def test_unsigned(self):
        self.pgp_tester.set_new_email(self.emails['signed'])
        self.assertTrue(self.pgp_tester.properties['signed'])

    def test_wrong_key(self):
        # tododta this needs test key
        pass

if __name__ == '__main__':
    unittest.main()
