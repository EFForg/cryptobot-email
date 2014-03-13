#!/usr/bin/env python

import os
import unittest
import bot
import unsubscribe
import email
import random
import sys
import jinja2

from sqlalchemy.ext.declarative import declarative_base
SQLAlchemyBase = declarative_base()

class GnuPGTest(unittest.TestCase):
    def setUp(self):
        # test keys
        self.public_key = open('test/keys/public.key').read()
        self.private_key = open('test/keys/private.key').read()
        # set up test keyring
        self.gpg = bot.GnuPG("test/homedir")
        self.gpg.import_keys(self.public_key)
        self.gpg.import_keys(self.private_key)

    def tearDown(self):
        pass

    def test_export_keys_valid(self):
        pubkey = self.gpg.export_keys('0D4AF6E8D289BDE46594D41255BB44BA0D3E5387')
        self.assertEqual(pubkey, self.public_key)
    
    def test_export_keys_invalid(self):
        pubkey = self.gpg.export_keys('0000000000000000000000000000000000000000')
        self.assertFalse(pubkey)

    def test_import_keys_valid(self):
        rms_pubkey = open('test/keys/rms.asc').read()
        fingerprint = self.gpg.import_keys(rms_pubkey)
        self.assertTrue(fingerprint)
        self.assertEqual(fingerprint.upper(), '6F818B215E159EF3FA26B0BE624DC565135EA668')
    
    def test_import_keys_invalid(self):
        fingerprint = self.gpg.import_keys('fail')
        self.assertFalse(fingerprint)

    def test_decrypt_valid(self):
        ciphertext = open('test/keys/test_decrypt_valid.asc').read()
        plaintext, signed = self.gpg.decrypt(ciphertext)
        self.assertEqual(plaintext, 'This is a test message.\n')
    
    def test_decrypt_invalid(self):
        ciphertext = open('test/keys/test_decrypt_invalid.asc').read()
        plaintext, signed = self.gpg.decrypt(ciphertext)
        self.assertFalse(plaintext)
    
    def test_encrypt(self):
        ciphertext = self.gpg.encrypt('test', '0D4AF6E8D289BDE46594D41255BB44BA0D3E5387')
        self.assertFalse(ciphertext == False)
        self.assertTrue(bot.PGP_ARMOR_HEADER_MESSAGE in ciphertext)

    def test_sign(self):
        sig = self.gpg.sign('test')
        self.assertTrue(bot.PGP_ARMOR_HEADER_SIGNATURE in sig)
    
    def test_has_secret_key_with_uid(self):
        self.assertEqual('0D4AF6E8D289BDE46594D41255BB44BA0D3E5387', self.gpg.has_secret_key_with_uid('OpenPGPBot Test Suite (insecure) <invalid_and_insecure@openpgpbot.eff.org>'))
        self.assertEqual('0D4AF6E8D289BDE46594D41255BB44BA0D3E5387', self.gpg.has_secret_key_with_uid('invalid_and_insecure@openpgpbot.eff.org'))
        self.assertFalse(self.gpg.has_secret_key_with_uid('fluff'))

    def test_has_public_key_with_uid(self):
        expected_uid = 'OpenPGPBot Test Suite (insecure) <invalid_and_insecure@openpgpbot.eff.org>'
        self.assertTrue(self.gpg.has_public_key_with_uid('0D4AF6E8D289BDE46594D41255BB44BA0D3E5387', expected_uid))
        self.assertFalse(self.gpg.has_public_key_with_uid('0D4AF6E8D289BDE46594D41255BB44BA0D3E5387', 'fluff'))

    @unittest.skipUnless('--slow' in sys.argv, "Skippings slow key generation")
    def test_gen_key(self):
        print >>sys.stderr, "\nTesting key generation. This may take some time.\n"
        random.seed()
        r = random.random()
        name = 'Test '+str(r)
        expected_uid = name+' <test@example.com>'
        fingerprint = self.gpg.gen_key(name, 'test@example.com', 1024)
        self.assertTrue(self.gpg.has_secret_key_with_uid(expected_uid))

class BotTest(unittest.TestCase):

    def setUp(self):
        # test keys
        self.public_key = open('test/keys/public.key').read()
        self.private_key = open('test/keys/private.key').read()
        # set up test keyring
        self.gpg = bot.GnuPG("test/homedir")
        self.gpg.import_keys(self.public_key)
        self.gpg.import_keys(self.private_key)
        
        # set up tester
        self.emails = {}
        for filename in os.listdir('test/emails/'):
            self.emails[filename] = email.message_from_string(open('test/emails/'+filename).read())

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

class EmailSenderTest(unittest.TestCase):

    def setUp(self):
        self.reply_body = None
        self.reply_from = None
        self.reply_to = None
        template_loader = jinja2.FileSystemLoader(searchpath="templates")
        self.env = jinja2.Environment(loader=template_loader, trim_blocks=True)


        # test keys
        self.public_key = open('test/keys/public.key').read()
        self.private_key = open('test/keys/private.key').read()
        # set up test keyring
        self.gpg = bot.GnuPG("test/homedir")
        self.gpg.import_keys(self.public_key)
        self.gpg.import_keys(self.private_key)
 
        # set up tester
        self.emails = {}
        for filename in os.listdir('test/emails/'):
            self.emails[filename] = email.message_from_string(open('test/emails/'+filename).read())

    def get_mock_sender(outer_self):
        def mock_sender(msg_string, from_email, to_email, s=outer_self):
            s.reply_body = msg_string
            s.reply_from = from_email
            s.reply_to = to_email
        return mock_sender

    def test_unencrypted_message_reply_address(self):
        msg = bot.OpenPGPMessage(self.emails['unencrypted_thunderbird'],
                                 gpg=self.gpg)
        bot.EmailSender(msg, self.env, fingerprint= '0D4AF6E8D289BDE46594D41255BB44BA0D3E5387',  sender=self.get_mock_sender())
        self.assertTrue('justtesting@example.com' in self.reply_to)

class UnsubscribeTest(unittest.TestCase):
    def setUp(self):
      self.db = unsubscribe.getDatabase('sqlite:///test/homedir/test.db', setup=True)

    def tearDown(self):
      unsubscribe.BlockedEmail.metadata.drop_all(self.db.engine)

    def test_add(self):
      self.db.add('test@example.com')
      self.assertTrue(self.db.find('test@example.com') is not None)


if __name__ == '__main__':
    try:
        sys.argv.remove('--slow')
    except ValueError:
        pass
    unittest.main()
