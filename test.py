#!/usr/bin/env python

import os
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
        self.emails = {}
        for filename in os.listdir('test_emails/'):
            self.emails[filename] = email.message_from_string(open('test_emails/'+filename).read())

    def tearDown(self):
        pass

    def test_unencrypted(self):
        msg = bot.OpenPGPMessage(self.emails['unencrypted_thunderbird'],
                                 gpg=self.gpg)
        self.assertFalse(msg.encrypted_right)
        self.assertFalse(msg.encrypted_wrong)

    def test_signed(self):
        msg = bot.OpenPGPMessage(self.emails['signed'],
                                 gpg=self.gpg)
        self.assertTrue(msg.signed)
        
    def test_unsigned(self):
        # todo finish
        pass

    def test_encrypted_correct_key(self):
        result_text = "encrypted text"
        msg = bot.OpenPGPMessage(self.emails['encrypted_correctly'],
                                 gpg=self.gpg)
        self.assertTrue(msg.encrypted_right)
        self.assertFalse(msg.encrypted_wrong)
        self.assertEquals(result_text, msg.decrypted_text.split("quoted-printable")[1].strip())
    
    def test_encrypted_wrong_key(self):
        msg = bot.OpenPGPMessage(self.emails['encrypted_to_wrong_key'],
                                 gpg=self.gpg)
        self.assertFalse(msg.encrypted_right)
        self.assertTrue(msg.encrypted_wrong)

    def test_encrypted_and_signed_pgp_mime(self):
        result_text = "this message is encrypted and signed and uses pgp/mime"
        msg = bot.OpenPGPMessage(self.emails['encrypted_signed_pgp_mime'], gpg=self.gpg)
        self.assertTrue(msg.encrypted_right)
        self.assertFalse(msg.encrypted_wrong)
        self.assertTrue(msg.decrypted_text.find(result_text) > 0)
        self.assertTrue(msg.signed)

    def test_pubkey_included_attached_text_plain(self):
        msg = bot.OpenPGPMessage(self.emails['pubkey_attached_text-plain'], gpg=self.gpg)
        self.assertTrue(msg.pubkey_included)
    
    def test_pubkey_included_attached_application_pgpkeys(self):
        msg = bot.OpenPGPMessage(self.emails['pubkey_attached_application-pgpkeys'], gpg=self.gpg)
        self.assertTrue(msg.pubkey_included)

    def test_pubkey_included_inline(self):
        msg = bot.OpenPGPMessage(self.emails['pubkey_inline'], gpg=self.gpg)
        self.assertTrue(msg.pubkey_included)

    def test_encrypted_pubkey_included_attached_text_plain(self):
        msg = bot.OpenPGPMessage(self.emails['encrypted_pubkey_attached_text-plain'], gpg=self.gpg)
        self.assertTrue(msg.encrypted_right)
        self.assertTrue(msg.pubkey_included)
    
    def test_encrypted_pubkey_included_attached_application_pgpkeys(self):
        msg = bot.OpenPGPMessage(self.emails['encrypted_pubkey_attached_application-pgpkeys'], gpg=self.gpg)
        self.assertTrue(msg.encrypted_right)
        self.assertTrue(msg.pubkey_included)

    def test_encrypted_pubkey_included_inline(self):
        msg = bot.OpenPGPMessage(self.emails['encrypted_pubkey_inline'], gpg=self.gpg)
        self.assertTrue(msg.encrypted_right)
        self.assertTrue(msg.pubkey_included)

if __name__ == '__main__':
    unittest.main()
