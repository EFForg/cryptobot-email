#!/usr/bin/env python

import unittest
import bot
import email
import gnupg

class BotTest(unittest.TestCase):

    def setUp(self):
        # test keys
        self.public_key = open('test_key/public.key').read()
        self.private_key = open('test_key/private.key').read()
        # set up test keyring
        self.gpg = gnupg.GPG(homedir="test_bot_keyring")
        self.gpg.import_keys(self.public_key)
        self.gpg.import_keys(self.private_key)
        
        # set up tester
        self.pgp_tester = bot.OpenPGPEmailParser(gpg=self.gpg)
        self.emails = {
            'encrypted_to_wrong_key': email.message_from_string(open('test_emails/encrypted_to_wrong_key').read()),
            'signed': email.message_from_string(open('test_emails/signed').read()),
            'unencrypted_thunderbird': email.message_from_string(open('test_emails/unencrypted_thunderbird').read()),
            'encrypted_correctly': email.message_from_string(open('test_emails/encrypted_correctly').read())
        }


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

    def test_encrypted_wrong_key(self):
        # tododta fill this out
        pass

    def test_encrypted_correct_key(self):
        self.pgp_tester.set_new_email(self.emails['encrypted_correctly'])
        result_text = "encrypted text"
        self.assertEquals(result_text, self.pgp_tester.decrypted_text.split("quoted-printable")[1].strip())


if __name__ == '__main__':
    unittest.main()
