#!/usr/bin/env python
"""
An email bot to help you learn OpenPGP!
"""

import sys
import imaplib, smtplib
import email
from email.mime.text import MIMEText
import gnupg

PGP_ARMOR_HEADER_MESSAGE   = "-----BEGIN PGP MESSAGE-----"
PGP_ARMOR_HEADER_SIGNATURE = "-----BEGIN PGP SIGNATURE-----"

try:
    import config
except ImportError:
    print >> sys.stderr, "Error: could not load configuration from config.py"
    sys.exit(1)

class EmailFetcher(object):
    def __init__(self):
        pass

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

class EmailSender(object):
    def __init__(self, message, pgp_tester):
        self.message = message
        self.pgp_tester = pgp_tester

        # who to respond to?
        to_email = None
        if 'Reply-To' in message:
            to_email = message['Reply-To']
        elif 'From' in message:
            to_email = message['From']
        if not to_email:
            print 'Cannot decide who to respond to '
            return

        # what the response subject should be
        if 'Subject' in message:
            if subject[:4] != 'Re: '
                subject = 'Re: '+message['Subject']
            else:
                subject = message['Subject']
        else:
            subject = 'OpenPGPBot response'

        # todo: make a response template based on information in pgp_tester (#2)
        body = 'This is an OpenPGPBot response!'

        from_email = '{0} <{1}>'.format(config.PGP_NAME, config.PGP_EMAIL)
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = from_email
        msg['To'] = to_email

        s = smtplib.SMTP_SSL(config.SMTP_SERVER)
        s.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
        s.sendmail(from_email, [to_email], msg.as_string())
        s.quit()
        print 'Responded to {0}'.format(message['From'])

    def sign_body(self):
        # need to implement PGP/MIME to sign the body here
        pass
    
    def encrypt_body(self):
        # need to implement PGP/MIME to sign the body here
        pass

class OpenPGPEmailParser(object):
    def __init__(self, gpg=None, email=None):
        if not gpg:
            self.gpg = gnupg.GPG(homedir="bot_keyring")
        else:
            self.gpg = gpg
        self.set_new_email(email)

    # todo: reincorporate check_keypair where appropriate
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

    def set_new_email(self, email):
        self.email = email
        self.properties = {}
        self.is_pgp_email()

    def is_pgp_email(self):
        # XXX: rough heuristic. This is probably quite nuanced among different
        # clients.
        # 1. Multipart and non-multipart emails
        # 2. ASCII armored and non-armored emails
        if not self.email:
            return
        encrypted, signed = False, False
        for part in self.email.walk():
            if part.get_content_type() in ("text/plain", "text/html",
                    "application/pgp-signature", "application/octet-stream"):
                payload = part.get_payload().strip()
                if PGP_ARMOR_HEADER_MESSAGE in payload:
                    encrypted = True
                    # try to decrypt
                    self.decrypted_text = str(self.gpg.decrypt(payload))
                elif PGP_ARMOR_HEADER_SIGNATURE in payload:
                    signed = True
                else:
                    # TODO: might not be ASCII armored. Trial
                    # decryption/verification?
                    pass
        self.properties['encrypted'] = encrypted
        self.properties['signed'] = signed


def main():
    fetcher = EmailFetcher()
    pgp_tester = OpenPGPEmailParser()
    imap_conn, message_ids, messages = fetcher.get_all_mail()
    for message in messages:
        pgp_tester.set_new_email(message)

        if pgp_tester.properties['encrypted']:
            print '"%s" from %s is encrypted' % (message['Subject'], message['From'])
        if pgp_tester.properties['signed']:
            print '"%s" from %s is signed' % (message['Subject'], message['From'])

        # respond to the email
        EmailSender(message, pgp_tester)

        # delete the email



if __name__ == "__main__":
    main()
