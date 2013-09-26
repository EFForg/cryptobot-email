#!/usr/bin/env python
"""
An email bot to help you learn OpenPGP!
"""

from mailbox import Message, Maildir
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

    def get_maildir_mail(self):
        # todo: improve this function and make return values consistent
        Maildir.colon = '!'
        md = Maildir(config.MAILDIR)
        emails = []
        for key, message in md.iteritems():
            print 'Message is {0}'.format(message)
            emails.append(OpenPGPMessage(str(message), key))
            md.discard(key)
        return emails

    def get_imap_mail(self):
        self.imap_mail.select("inbox")
        # Get all email in the inbox (with uids instead of sequential ids)
        result, data = self.imap_mail.uid('search', None, "ALL")
        # result should be 'OK'
        # data is a list with a space separated list of ids
        message_ids = data[0].split()
        messages = []
        for message_id in message_ids:
            result, data = self.imap_mail.uid('fetch', message_id, "(RFC822)")
            messages.append(OpenPGPMessage(message=data[0][1],
                                           message_id=message_id))
        return messages

    def get_all_mail(self):
        if self.maildir:
            return self.get_maildir_mail()
        else:
            return self.get_imap_mail()

    def delete(self, message_id):
        if self.maildir:
            pass
        else:
            self.imap_mail.uid('store', message_id, '+FLAGS', '\\Deleted')

class EmailSender(object):
    def __init__(self, message, env):
        self.message = message
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

        # make a response template based on information in OpenPGPMessage (#2)
        # todo: do this for plain txt emails too
        html_template = self.env.get_template('email_template.html')

        # todo: this if/else logic should be handled by templating
        if self.message.encrypted:
            encrypted_html = '<h3 style="color:green"> Your email was encrypted <h3>'
        else:
            encrypted_html = '<h3 style="color:red"> Your email was NOT encrypted <h3>'
        if self.message.signed:
            signed_html = '<h3 style="color:green"> Your email was signed <h3>'
        else:
            signed_html = '<h3 style="color:red"> Your email was NOT signed <h3>'

        html_template_vars = {'encrypted_html' : encrypted_html,
                              'signed_html': signed_html}
        html_body = html_template.render(html_template_vars)

        txt_body = 'This is a OpenPGPBot txt response. Sorry only html works right now!'

        # support both html and plain text responses
        txt_part = MIMEText(txt_body, 'plain')
        html_part = MIMEText(html_body, 'html')
    
        msg.attach(txt_part)
        msg.attach(html_part)
        self.send_email(msg, from_email, to_email)

    def send_email(self, msg, from_email, to_email):
        if config.SMTP_SERVER == 'localhost':
            s = smtplib.SMTP(config.SMTP_SERVER)
        else:
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

class OpenPGPMessage(Message):
    """Email message with OpenPGP-specific properties"""

    def __init__(self, message, message_id=None, gpg=None):
        Message.__init__(self, message)
        self._message_id = message_id
        if not gpg:
            self._gpg = gnupg.GPG(homedir=config.GPG_HOMEDIR)
        else:
            self._gpg = gpg
        self._parse_for_openpgp()

    @property
    def message_id(self):
        return self._message_id

    def _parse_for_openpgp(self):
        # XXX: rough heuristic. This is probably quite nuanced among different
        # clients.
        # 1. Multipart and non-multipart emails
        # 2. ASCII armored and non-armored emails
        self._encrypted, self._signed = False, False
        for part in self.walk():
            # tododta remove; debugging
            #print "part is {0}".format(str(part))
            #print "part.get_content_type() is {0}".format(str(part.get_content_type()))
            if part.get_content_type() in ("text/plain", "text/html",
                    "application/pgp-signature", "application/octet-stream"):
                payload = part.get_payload().strip()
                if PGP_ARMOR_HEADER_MESSAGE in payload:
                    self._encrypted = True
                    # try to decrypt
                    self._decrypted_text = str(self._gpg.decrypt(payload))
                elif PGP_ARMOR_HEADER_SIGNATURE in payload:
                    self._signed = True
                else:
                    # TODO: might not be ASCII armored. Trial
                    # decryption/verification?
                    pass

    @property
    def encrypted(self):
        return self._encrypted

    @property
    def signed(self):
        return self._signed

    @property
    def decrypted_text(self):
        return self._decrypted_text

def main():
    # jinja2
    templateLoader = jinja2.FileSystemLoader(searchpath="templates")
    templateEnv = jinja2.Environment(loader=templateLoader)
    # email fetcher
    fetcher = EmailFetcher(maildir=config.USE_MAILDIR)
    messages = fetcher.get_all_mail()
    for message in messages:
        if message.encrypted:
            print '"%s" from %s is encrypted' % (message['Subject'], message['From'])
        if message.signed:
            print '"%s" from %s is signed' % (message['Subject'], message['From'])

        # respond to the email
        EmailSender(message, templateEnv)

        # delete the email
        # (note: by default Gmail ignores the IMAP standard and archives email instead of deleting it
        #  http://gmailblog.blogspot.com/2008/10/new-in-labs-advanced-imap-controls.html )
        fetcher.delete(message.message_id)

def check_bot_keypair():
    """Make sure the bot has a keypair. If it doesn't, create one."""
    gpg = gnupg.GPG(homedir=config.GPG_HOMEDIR)

    expected_uid = '{0} <{1}>'.format(config.PGP_NAME, config.PGP_EMAIL)
    gen_new_key, fingerprint = True, None
    for key in gpg.list_keys(secret=True):
        for uid in key['uids']:
            if str(uid) == expected_uid:
                fingerprint = str(key['fingerprint'])
                gen_new_key = False

    if gen_new_key:
        print 'Generating new OpenPGP keypair with user ID: {0}'.format(expected_uid)
        gpg_input = gpg.gen_key_input(name_email=config.PGP_EMAIL,
                                      name_real=config.PGP_NAME,
                                      key_type='RSA',
                                      key_length=4096)
        key = gpg.gen_key(gpg_input)
        fingerprint = str(key.fingerprint)
        print 'Finished generating keypair. Fingerprint is: {0}'.format(fingerprint)

    return fingerprint

if __name__ == "__main__":
    check_bot_keypair()
    main()
