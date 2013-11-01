#!/usr/bin/env python
"""
An email bot to help you learn OpenPGP!
"""

from mailbox import Message, Maildir
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import sys, os, subprocess
import imaplib, smtplib
import email
import jinja2

PGP_ARMOR_HEADER_MESSAGE   = "-----BEGIN PGP MESSAGE-----"
PGP_ARMOR_HEADER_SIGNATURE = "-----BEGIN PGP SIGNATURE-----"

try:
    import config
except ImportError:
    print >> sys.stderr, "Error: could not load configuration from config.py"
    sys.exit(1)

class GnuPG(object):
    def __init__(self, homedir=False):
        if not homedir:
            self.homedir = config.GPG_HOMEDIR
        else:
            self.homedir = homedir

    def export_keys(self, fingerprint):
        """Returns an ascii armorer public key block, or False"""
        out, err = self._gpg(['--armor', '--no-emit-version', '--export', fingerprint])
        if out == 'gpg: WARNING: nothing exported\n':
            return False
        else:
            return out
    
    def import_keys(self, pubkey):
        """Imports a public key block and returns a fingerprint, or False of invalid pubkey"""

        # figure out the fingerprint of the key
        fingerprint = False
        out, err = self._gpg(['--with-fingerprint'], pubkey)
        for line in out.split('\n'):
            if 'Key fingerprint = ' in line:
                fingerprint = line.strip().lstrip('Key fingerprint = ').replace(' ', '')
        if not fingerprint:
            return False

        # import the key
        self._gpg(['--import'], pubkey)
        return fingerprint

    def decrypt(self, ciphertext):
        """Attempts to decrypt ciphertext block, returns plaintext or False if decryption fails"""
        out, err = self._gpg(['--decrypt'], ciphertext)
        if 'secret key not available' in err:
            return False
        return out
    
    def encrypt(self, plaintext, fingerprint):
        """Encrypts plaintext, returns ciphertext"""
        out, err = self._gpg(['--armor', '--batch', '--trust-model', 'always', '--encrypt', '--recipient', fingerprint], plaintext)

        if 'encryption failed' in err:
            return False

        return out

    def has_secret_key_with_uid(self, uid):
        """Searches secret keys for uid, and if it finds one returns the fingerprint, otherwise False"""
        out, err = self._gpg(['--list-secret-keys', '--with-colons'])
        for line in out.split('\n'):
            if line[0:3] == 'sec' or line[0:3] == 'uid':
                if uid in line:
                    return True
        return False

    def gen_key(self, name, email, key_length=4096):
        """Generate a key, returns its key ID"""
        
        # make input variable to pass into gpg
        input  = "Key-Type: RSA\n"
        input += "Key-Length: "+str(key_length)+"\n"
        input += "Name-Real: "+name+"\n"
        input += "Name-Email: "+email+"\n"
        input += "%commit\n"

        out, err = self._gpg(['--gen-key', '--batch', '--no-tty'], input)

        # it doesn't seem to be easy to get the full fingerprint, but return the key ID at least
        keyid = False
        for line in err:
            if 'marked as ultimately trusted' in line:
                keyid = line.strip().lstrip('gpg: key ').rstrip(' marked as ultimately trusted')
        return keyid

    def _gpg(self, args, input=None):
        gpg_args = ['gpg', '--homedir', self.homedir, '--no-tty'] + args
        p = subprocess.Popen(gpg_args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        return p.communicate(input)

class EmailFetcher(object):
    def __init__(self, use_maildir=False):
        self.use_maildir = use_maildir

        if not self.use_maildir:
            self.login(config.IMAP_USERNAME, config.IMAP_PASSWORD, config.IMAP_SERVER)

    def __del__(self):
        if not self.use_maildir:
            self.imap_mail.expunge()

    def login(self, username, password, imap_server):
        self.imap_mail = imaplib.IMAP4_SSL(imap_server)
        self.imap_mail.login(username, password)

    def get_maildir_mail(self):
        # Note: there is an issue where if msg is rfc822.Message,
        # then str(msg) does not print the full message. Hence trying
        # to use Maildir to import Messages, then get their string representations
        # to import into OpenPGPMessage failed, as did importing directly
        # since OpenPGPMessage expects a string. Instead we use os.walk to 
        # get Maildir files directly
        emails = []
        for file_path in os.walk(config.MAILDIR):
            for f in file_path[2]:
                if (f.endswith('openpgpbot')):
                    # this is a new email, and a horrible hack
                    # todo: more elegantly get file path
                    full_file_path = os.path.join(config.MAILDIR, 'new', f)
                    emails.append(OpenPGPMessage(open(full_file_path).read(), f.split('.')[0]))
                    os.remove(full_file_path)
        # todo delete email!
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
        if self.use_maildir:
            return self.get_maildir_mail()
        else:
            return self.get_imap_mail()

    def delete(self, message_id):
        if self.use_maildir:
            pass
        else:
            self.imap_mail.uid('store', message_id, '+FLAGS', '\\Deleted')

class EmailSender(object):
    def __init__(self, message, env, fp):
        self.message = message
        self.env = env
        self.fp = fp
        
        self.html_template = self.env.get_template('email_template.html')
        self.txt_template = self.env.get_template('email_template.txt')

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
                subject = self.message['Subject']
        else:
            subject = 'OpenPGPBot response'

        from_email = '{0} <{1}>'.format(config.PGP_NAME, config.PGP_EMAIL)

        msg = MIMEMultipart('mixed')
        msg['Subject'] = subject
        msg['From'] = from_email
        msg['To'] = to_email

        body = MIMEMultipart('alternative')

        # make a response template based on information in OpenPGPMessage (#2)
        template_vars = {
            'encrypted_right': self.message.encrypted_right,
            'encrypted_wrong': self.message.encrypted_wrong,
            'signed': self.message.signed
        }
        body.attach(MIMEText(self.txt_template.render(template_vars), 'plain'))
        body.attach(MIMEText(self.html_template.render(template_vars), 'html'))
        msg.attach(body)

        # if the message is not encrypted, attach public key (#16)
        if not self.message.encrypted_right:
            gpg = GnuPG()
            pubkey = str(gpg.export_keys(self.fp))
            pubkey_filename = '{0} {1} (0x{2}) pub.asc'.format(config.PGP_NAME, config.PGP_EMAIL, str(self.fp)[:-8])

            pubkey_part = MIMEBase('application', 'pgp-keys')
            pubkey_part.set_payload(pubkey)
            pubkey_part.add_header('Content-Disposition', 'attachment; filename="%s"' % pubkey_filename)
            msg.attach(pubkey_part)

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
            self._gpg = GnuPG()
        else:
            self._gpg = gpg
        self._parse_for_openpgp()

    @property
    def message_id(self):
        return self._message_id

    def _find_email_payload_matches(self, content_types, payload_test):
        matches = []
        for part in self.walk():
            if part.get_content_type() in content_types:
                payload = part.get_payload().strip()
                if payload_test in payload:
                    matches.append(payload)
        return matches

    def _parse_for_openpgp(self):
        # XXX: rough heuristic. This is probably quite nuanced among different
        # clients.
        # 1. Multipart and non-multipart emails
        # 2. ASCII armored and non-armored emails
        self._encrypted_right, self._encrypted_wrong, self._signed, self._pubkey_included = False, False, False, False
        content_types = ["text/plain", "text/html",
                         "application/pgp-signature", "application/octet-stream"]
        encrypted_parts = self._find_email_payload_matches(content_types, PGP_ARMOR_HEADER_MESSAGE)
        if encrypted_parts:
            if len(encrypted_parts) > 1:
                # todo: raise error here?
                print "More than one encrypted part in this message. That's weird..."
            self._full_decrypted_text = self._gpg.decrypt(encrypted_parts[0])
            if not self._full_decrypted_text:
                self._encrypted_wrong = True
            else:
                self._encrypted_right = True
            # todo: check signatures in decrypted text
            self._decrypted_text = str(self._full_decrypted_text)
        signed_parts = self._find_email_payload_matches(content_types, PGP_ARMOR_HEADER_SIGNATURE)
        if signed_parts:
            if len(signed_parts) > 1:
                # todo: raise error here?
                print "More than one signed part in this message. That's weird..."
            self._signed = True
            # todo: check signature, public key attached, etc
        # TODO: might not be ASCII armored. Trial
        # decryption/verification?

    @property
    def encrypted_right(self):
        return self._encrypted_right
    
    @property
    def encrypted_wrong(self):
        return self._encrypted_wrong

    @property
    def signed(self):
        return self._signed

    @property
    def decrypted_text(self):
        return self._decrypted_text

    @property
    def pubkey_included(self):
        return self._pubkey_included

def main(fp):
    # jinja2
    template_loader = jinja2.FileSystemLoader(searchpath="templates")
    template_env = jinja2.Environment(loader=template_loader, trim_blocks=True)

    # email fetcher
    fetcher = EmailFetcher(use_maildir=config.USE_MAILDIR)
    messages = fetcher.get_all_mail()
    for message in messages:
        if message.encrypted_right:
            print '"%s" from %s is encrypted' % (message['Subject'], message['From'])
        if message.encrypted_wrong:
            print '"%s" from %s is encrypted to the wrong key' % (message['Subject'], message['From'])
        if message.signed:
            print '"%s" from %s is signed' % (message['Subject'], message['From'])

        # respond to the email
        EmailSender(message, template_env, fp)

        # delete the email
        # (note: by default Gmail ignores the IMAP standard and archives email instead of deleting it
        #  http://gmailblog.blogspot.com/2008/10/new-in-labs-advanced-imap-controls.html )
        fetcher.delete(message.message_id)

def check_bot_keypair(allow_new_key):
    """Make sure the bot has a keypair. If it doesn't, create one if allow_new_key is true."""
    gpg = GnuPG()

    expected_uid = '{0} <{1}>'.format(config.PGP_NAME, config.PGP_EMAIL)
    
    fingerprint = gpg.has_secret_key_with_uid(expected_uid)
    if not fingerprint:
        if allow_new_key:
            print 'Generating new OpenPGP keypair with user ID: {0}'.format(expected_uid)
            fingerprint = gpg.gen_key(config.PGP_NAME, config.PGP_EMAIL)
            print 'Finished generating keypair. Fingerprint is: {0}'.format(fingerprint)
        else:
            raise ValueError, "Could not find keypair for cryptobot"

    return fingerprint

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Cryptobot arg parser")
    parser.add_argument('--generate-new-key',dest='allow_new_key',action='store_true')
    parser.add_argument('--no-generate-new-key',dest='allow_new_key',action='store_false')
    parser.set_defaults(allow_new_key=False)
    args = parser.parse_args()

    print args.allow_new_key

    fp = check_bot_keypair(args.allow_new_key)
    main(fp)
