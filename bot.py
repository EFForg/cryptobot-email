#!/usr/bin/env python
"""
An email bot to help you learn OpenPGP!
"""

import sys
import imaplib
import email
import gnupg

PGP_ARMOR_HEADER_MESSAGE   = "-----BEGIN PGP MESSAGE-----"
PGP_ARMOR_HEADER_SIGNATURE = "-----BEGIN PGP SIGNATURE-----"

try:
    import config
except ImportError:
    print >> sys.stderr, "Error: could not load configuration from config.py"
    sys.exit(1)

class OpenPGPBot(object):
    def __init__(self):
        self.gpg = gnupg.GPG(homedir="bot_keyring")
        self.seckey_fp = self.check_keypair()

    def login(self, username, password, imap_server):
        mail = imaplib.IMAP4_SSL(imap_server)
        mail.login(username, password)
        return mail

    def get_all_mail(self):
        mail = self.login(config.IMAP_USERNAME, config.IMAP_PASSWORD, config.IMAP_SERVER)
        mail.select("inbox")
        # Get all email in the inbox (with uids instead of sequential ids)
        result, data = mail.uid('search', None, "ALL")
        # result should be 'OK'
        # data is a list with a space separated list of ids
        message_ids = data[0].split()
        messages = []
        for message_id in message_ids:
            # fetch the email body (RFC822) for the given ID
            result, data = mail.uid('fetch', message_id, "(RFC822)")
            # convert raw email body into EmailMessage
            messages.append(email.message_from_string(data[0][1]))
        return mail, message_ids, messages

    def check_keypair(self):
        gen_new_key = True
        expected_uid = '{0} <{1}>'.format(config.PGP_NAME, config.PGP_EMAIL)
        fingerprint = None

        seckeys = self.gpg.list_keys(secret=True)
        if len(seckeys):
            for key in seckeys:
                for uid in key['uids']:
                    if str(uid) == expected_uid:
                        fingerprint = str(key['fingerprint'])
                        gen_new_key = False

        if gen_new_key:
            print 'Generating new OpenPGP keypair with user ID: {0}'.format(expected_uid)
            gpg_input = self.gpg.gen_key_input(name_email=config.PGP_EMAIL, 
                                          name_real=config.PGP_NAME, 
                                          key_type='RSA',
                                          key_length=4096)
            key = self.gpg.gen_key(gpg_input)
            fingerprint = str(key.fingerprint)
        
        return fingerprint


class OpenPGPEmailParser(object):
    def __init__(self, email=None):
        self.email = email

    def set_new_email(self, email):
        self.email = email
        self.properties = {}

    def is_pgp_email(self):
        # XXX: rough heuristic. This is probably quite nuanced among different
        # clients.
        # 1. Multipart and non-multipart emails
        # 2. ASCII armored and non-armored emails
        encrypted, signed = False, False
        for part in self.email.walk():
            if part.get_content_type() in ("text/plain", "text/html",
                    "application/pgp-signature", "application/octet-stream"):
                payload = part.get_payload()
                if PGP_ARMOR_HEADER_MESSAGE in payload:
                    encrypted = True
                elif PGP_ARMOR_HEADER_SIGNATURE in payload:
                    signed = True
                else:
                    # TODO: might not be ASCII armored. Trial
                    # decryption/verification?
                    pass
        self.properties['encrypted'] = encrypted
        self.properties['signed'] = signed


def main():
    pgp_tester = OpenPGPEmailParser()
    bot = OpenPGPBot()
    imap_conn, message_ids, messages = bot.get_all_mail()
    for message in messages:
        print "received message: %s" % message['Subject']
        pgp_tester.set_new_email(message)
        pgp_tester.is_pgp_email()
        if pgp_tester.properties['encrypted']:
            print '"%s" from %s is encrypted' % (message['Subject'], message['From'])
        if pgp_tester.properties['signed']:
            print '"%s" from %s is signed' % (message['Subject'], message['From'])


if __name__ == "__main__":
    main()
