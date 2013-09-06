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

def login(username, password, imap_server):
    mail = imaplib.IMAP4_SSL(imap_server)
    mail.login(username, password)
    return mail

def get_all_mail():
    mail = login(config.USERNAME, config.PASSWORD, config.IMAP_SERVER)
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

class OpenPGPEmailParser(object):
    def __init__(self):
        pass

    def is_pgp_email(self, email):
        # XXX: rough heuristic. This is probably quite nuanced among different
        # clients.
        # 1. Multipart and non-multipart emails
        # 2. ASCII armored and non-armored emails
        encrypted, signed = False, False
        for part in email.walk():
            if part.get_content_type() in ("text/plain", "text/html",
                    "application/pgp-signature"):
                payload = part.get_payload()
                if PGP_ARMOR_HEADER_MESSAGE in payload:
                    encrypted = True
                elif PGP_ARMOR_HEADER_SIGNATURE in payload:
                    signed = True
                else:
                    # TODO: might not be ASCII armored. Trial
                    # decryption/verification?
                    pass
        return encrypted, signed

def main():
    pgp_tester = OpenPGPEmailParser()
    gpg = gnupg.GPG(homedir="bot_keyring")
    imap_conn, message_ids, messages = get_all_mail()
    for message in messages:
        print "received message: %s" % message['Subject']
        encrypted, signed = pgp_tester.is_pgp_email(message)
        if encrypted:
            print '"%s" from %s is encrypted' % (message['Subject'], message['From'])
        if signed:
            print '"%s" from %s is signed' % (message['Subject'], message['From'])

if __name__ == "__main__":
    main()
