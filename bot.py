#!/usr/bin/env python
"""
An email bot to help you learn OpenPGP!
"""

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sys
import imaplib, smtplib
import email
import gnupg
import jinja2

PGP_ARMOR_HEADER_MESSAGE   = "-----BEGIN PGP MESSAGE-----"
PGP_ARMOR_HEADER_SIGNATURE = "-----BEGIN PGP SIGNATURE-----"

try:
    import config
except ImportError:
    print >> sys.stderr, "Error: could not load configuration from config.py"
    sys.exit(1)

class EmailFetcher(object):
    def __init__(self, maildir=False):
        self.maildir = maildir

        if not self.maildir:
            self.login(config.IMAP_USERNAME, config.IMAP_PASSWORD, config.IMAP_SERVER)

    def __del__(self):
        if not self.maildir:
            self.imap_mail.expunge()

    def login(self, username, password, imap_server):
        self.imap_mail = imaplib.IMAP4_SSL(imap_server)
        self.imap_mail.login(username, password)

    def get_maildir_directly(self):
        # todo: improve this function and make return values consistent
        import mailbox
        mailbox.Maildir.colon = '!'
        md = mailbox.Maildir(config.MAILDIR)
        return None, None, [email.message_from_string(str(msg)) for msg in md.values()]

    def get_imap_mail(self):
        self.imap_mail.select("inbox")
        # Get all email in the inbox (with uids instead of sequential ids)
        result, data = self.imap_mail.uid('search', None, "ALL")
        # result should be 'OK'
        # data is a list with a space separated list of ids
        message_ids = data[0].split()
        messages = []
        for message_id in message_ids:
            # fetch the email body (RFC822) for the given ID
            result, data = self.imap_mail.uid('fetch', message_id, "(RFC822)")
            # convert raw email body into EmailMessage
            messages.append(email.message_from_string(data[0][1]))
        return message_ids, messages

    def get_all_mail(self):
        if self.maildir:
            return self.get_maildir_directly()
        else:
            return self.get_imap_mail()

    def delete(self, message_id):
        if self.maildir:
            pass
        else:
            self.imap_mail.uid('store', message_id, '+FLAGS', '\\Deleted')

class EmailSender(object):
    def __init__(self, message, pgp_tester, env):
        self.message = message
        self.pgp_tester = pgp_tester
        self.env = env
        self.construct_and_send_email()

    def construct_and_send_email(self):
        # who to respond to?
        to_email = None
        if 'Reply-To' in self.message:
            to_email = self.message['Reply-To']
        elif 'From' in self.message:
            to_email = self.message['From']
        if not to_email:
            print 'Cannot decide who to respond to '
            return

        # what the response subject should be
        if 'Subject' in self.message:
            if self.message['Subject'][:4] != 'Re: ':
                subject = 'Re: '+self.message['Subject']
            else:
                subject = message['Subject']
        else:
            subject = 'OpenPGPBot response'

        from_email = '{0} <{1}>'.format(config.PGP_NAME, config.PGP_EMAIL)

        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = from_email
        msg['To'] = to_email

        # make a response template based on information in pgp_tester (#2)
        # todo: do this for plain txt emails too
        html_template = self.env.get_template('email_template.html')
        html_template_vars = {'encrypted_html' : '<h1> Dan test: your email is encrypted!</h1><br>',
                              'signed_html': '<h1> Dan test: your email is signed!</h1>'}
        html_body = html_template.render(html_template_vars)

        txt_body = 'This is a OpenPGPBot txt response.'


        # support both html and plain text responses
        txt_part = MIMEText(txt_body, 'plain')
        html_part = MIMEText(html_body, 'html')
    
        msg.attach(txt_part)
        msg.attach(html_part)
        self.send_email(msg, from_email, to_email)

    def send_email(self, msg, from_email, to_email):
        s = smtplib.SMTP_SSL(config.SMTP_SERVER)
        s.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
        s.sendmail(from_email, [to_email], msg.as_string())
        s.quit()
        print 'Responded to {0}'.format(self.message['From'])

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
    # todo? use fancier version of jinja2
    # e.g. 
    templateLoader = jinja2.FileSystemLoader(searchpath="templates")
    templateEnv = jinja2.Environment(loader=templateLoader)
    #env = Environment(loader=PackageLoader('OpenPGPBot', 'templates'))

    fetcher = EmailFetcher(maildir=config.MAILDIR)
    pgp_tester = OpenPGPEmailParser()
    message_ids, messages = fetcher.get_all_mail()
    for i in xrange(len(message_ids)):
        messages[i].message_id = message_ids[i]
    for message in messages:
        pgp_tester.set_new_email(message)

        if pgp_tester.properties['encrypted']:
            print '"%s" from %s is encrypted' % (message['Subject'], message['From'])
        if pgp_tester.properties['signed']:
            print '"%s" from %s is signed' % (message['Subject'], message['From'])

        # respond to the email
        EmailSender(message, pgp_tester, templateEnv)

        # delete the email
        # (note: by default Gmail ignores the IMAP standard and archives email instead of deleting it
        #  http://gmailblog.blogspot.com/2008/10/new-in-labs-advanced-imap-controls.html )
        fetcher.delete(message.message_id)

if __name__ == "__main__":
    main()
