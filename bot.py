#!/usr/bin/env python
"""
An email bot to help you learn OpenPGP!
"""

from mailbox import Message, Maildir
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.encoders import encode_quopri

from cStringIO import StringIO
from email.generator import Generator

import sys, os, subprocess
import imaplib, smtplib
import email
import jinja2
import rfc822
import quopri

PGP_ARMOR_HEADER_MESSAGE   = "-----BEGIN PGP MESSAGE-----"
PGP_ARMOR_HEADER_SIGNATURE = "-----BEGIN PGP SIGNATURE-----"
PGP_ARMOR_HEADER_PUBKEY    = "-----BEGIN PGP PUBLIC KEY BLOCK-----"
PGP_ARMOR_FOOTER_PUBKEY    = "-----END PGP PUBLIC KEY BLOCK-----"

try:
    import config
except ImportError:
    print >> sys.stderr, "Error: could not load configuration from config.py"
    sys.exit(1)

class GnuPG(object):
    """A wrapper around ``gpg`` executable

    This class implements no crypto itself; rather, it just calls ``gpg``
    with reasonable options.

    :ivar homedir: the GPG home directory. Will be created if it doesn't exist.
    """
    def __init__(self, homedir=False):
        self.homedir = homedir or config.GPG_HOMEDIR
        if not os.path.exists(self.homedir):
            os.mkdir(self.homedir, 0700)
        # XXX check permissions on existing directory and fix (or at least warn)?

    def export_keys(self, fingerprint):
        """Export an ascii-armored public key block

        :arg str fingerprint: the fingerprint of the key
        :rtype: str
        :returns: exported block; False if fingerprint not found or other error
        """
        out, err = self._gpg(['--armor', '--no-emit-version', '--export', fingerprint])
        if out == 'gpg: WARNING: nothing exported\n':
            return False
        else:
            return out

    def import_keys(self, pubkey):
        """Import a public key block

        :arg str pubkey: the public key
        :rtype: str
        :returns: fingerprint of the pubkey; False of invalid pubkey
        """
        # figure out the fingerprint of the key
        fingerprint = False
        out, err = self._gpg(['--with-fingerprint'], pubkey)
        for line in out.split('\n'):
            if 'Key fingerprint = ' in line:
                fingerprint = line.strip().lstrip('Key fingerprint = ').replace(' ', '')
        if not fingerprint:
            return False

        # import the key
        out, err = self._gpg(['--import'], pubkey)
        return fingerprint

    def decrypt(self, ciphertext):
        """Decrypt a ciphertext block to plaintext

        :arg str ciphertext: the encrypted bits
        :rtype: 2-tuple of (str, bool)
        :returns: 2-tuple of (plaintext, is_signed); False if decryption fails
        """
        out, err = self._gpg(['--decrypt'], ciphertext)

        if 'secret key not available' in err:
            return False, False

        signed = 'Good signature from' in err
        return out, signed

    def encrypt(self, plaintext, fingerprint):
        """Encrypts plaintext to a ciphertext block

        :arg str plaintext: the plaintext bits to be encrypted
        :arg str fingerprint: the fingerprint of the user to whom we should encrypt
        :rtype: str
        :returns: the encrypted bits; False on error
        """
        out, err = self._gpg(['--armor', '--batch', '--trust-model', 'always', '--encrypt', '--recipient', fingerprint], plaintext)

        if 'encryption failed' in err:
            return False

        return out

    def sign(self, message):
        """Sign a message

        :arg str message: the text to sign
        :rtype: str
        :returns: ASCII armored signature"""

        # note, this assumes you only have 1 secret key in your keyring.
        # it might make sense to add --default-key FINGERPRINT later.
        out, err = self._gpg(['--armor', '--detach-sign'], message)
        return out

    def has_secret_key_with_uid(self, uid):
        """Searches secret keys for a uid

        :arg str uid: the user id to search for
        :rtype: str
        :returns: fingerprint if uid was found; else False
        """
        ## When running gpg --list-secret-keys --with-colons --fingerprint, here is some sample output.

        ## sec::4096:1:061BDEF98CCDA4FA:2013-11-05::::CryptoBot Email <wsmfzz62@gmail.com>:::
        ## fpr:::::::::78C9B0F7289B460C823A2102061BDEF98CCDA4FA:

        ## Or, for more complicated output:

        ## sec::4096:1:B4D25A1E99999697:2011-06-24:2014-09-18:::Micah Lee <micah@eff.org>:::
        ## fpr:::::::::5C17616361BD9F92422AC08BB4D25A1E99999697:
        ## uid:::::::21C57F8639CA1D1D9A9F3BE78129ED0043C11693::Micah Lee <micahflee@gmail.com>:
        ## uid:::::::BEE1517245C07B111BEFC41EEB1CDEE5DF0847E0::Micah Lee <micahflee@riseup.net>:
        ## uid:::::::7573A1517811E970A01B05BCE2E48DD8FEFE647E::Micah Lee <micah@pressfreedomfoundation.org>:
        ## uid:::::::763D70011F3C02DD325865D92960346A49D07F4C::Micah Lee <micah@micahflee.com>:
        ## ssb::4096:1:CE8CDD55E8839F99:2011-06-24:::::::
        ## sec::2048:1:AF878F07E341E711:2012-02-24::::EFF Webmaster <webmaster@eff.org>:::
        ## fpr:::::::::1729DC3DB3F635D25B316984AF878F07E341E711:
        ## ssb::2048:1:80939142EB82ABA7:2012-02-24:::::::

        ## This loops through the output looking for a valid uid. If it finds
        ## one, it returns the fingerprint from the fpr line associated with
        ## that keypair. If the valid uid is the primary id, it's listed in
        ## the sec line (before fpr), but if it's a different uid it's listed
        ## in a uid line (after fpr). So it's confusing, but this seems to
        ## work.


        out, err = self._gpg(['--list-secret-keys', '--with-colons', '--fingerprint'])

        return_fp = False
        cur_fp = ''
        for line in out.split('\n'):
            if line[0:3] == 'fpr':
                cur_fp = line.lstrip('fpr:::::::::').rstrip(':')
                if return_fp:
                    return cur_fp
            if line[0:3] == 'sec' or line[0:3] == 'uid':
                if uid in line:
                    if cur_fp != '':
                        return cur_fp
                    return_fp = True
        return False

    def has_public_key_with_uid(self, fingerprint, uid):
        """Searches fingerprint's keyring for a uid

        :arg str fingerprint: the fingerprint of the keyring to search
        :arg str uid: the user id to search for
        :rtype: bool
        :returns: True if found
        """
        out, err = self._gpg(['--list-keys', '--with-colons', fingerprint])
        for line in out.split('\n'):
            if line[0:3] == 'pub' or line[0:3] == 'uid':
                if uid in line:
                    return True
        return False

    def gen_key(self, name, email, key_length=4096):
        """Generate a new key

        :arg str name: human-readable name of the key
        :arg str email: an email address for the key
        :arg int key_length: how many bits should the key be
        :rtype: str
        :returns: key ID of generated key"""

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
        """Helper function that calls ``gpg``. For internal use.

        :arg list args: list of additional commandline options
        :arg str input: string to feed to ``gpg`` stdin
        :rtype: 2-tuple of str
        :returns: 2-tuple of (stdout, stderr) from ``gpg`` call
        """

        gpg_args = ['gpg', '--homedir', self.homedir, '--no-tty'] + args
        p = subprocess.Popen(gpg_args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = p.communicate(input)
        return out, err

class EmailFetcher(object):
    """retrieve email from IMAP or maildir

    :ivar bool use_maildir: use maildir or IMAP
    :ivar imap_mail: IMAP server connection
    """
    # XXX this should be two (sub)classes, instead of dispatching on a flag

    def __init__(self, use_maildir=False):
        self.use_maildir = use_maildir

        if not self.use_maildir:
            self.login(config.IMAP_USERNAME, config.IMAP_PASSWORD, config.IMAP_SERVER)

    def __del__(self):
        # XXX this should be called explicitly. Avoid __del__!
        if not self.use_maildir:
            self.imap_mail.expunge()

    def login(self, username, password, imap_server):
        """login to IMAP server. For internal use.

        :arg str username: IMAP username
        :arg str password: IMAP password
        :arg str imap_server: hostname of IMAP server
        """
        # XXX should this take port & key/cert files for IMAP server? meh
        self.imap_mail = imaplib.IMAP4_SSL(imap_server)
        self.imap_mail.login(username, password)

    def get_maildir_mail(self):
        """retrieve emails from a maildir. For internal use.

        Mails will be deleted after reading.

        :rtype: list of :class:`OpenPGPMessage`
        """
        # Note: there is an issue where if msg is rfc822.Message,
        # then str(msg) does not print the full message. Hence trying
        # to use Maildir to import Messages, then get their string representations
        # to import into OpenPGPMessage failed, as did importing directly
        # since OpenPGPMessage expects a string. Instead we use os.walk to
        # get Maildir files directly
        emails = []
        for file_path in os.walk(config.MAILDIR):
            for f in file_path[2]:
                # XXX why this extension?
                if (f.endswith('openpgpbot')):
                    # this is a new email, and a horrible hack
                    # todo: more elegantly get file path
                    full_file_path = os.path.join(config.MAILDIR, 'new', f)
                    emails.append(OpenPGPMessage(open(full_file_path).read(), f.split('.')[0]))
                    os.remove(full_file_path)
        # todo delete email!
        # XXX bad comment? ^^ we're already deleting mails
        return emails

    def get_imap_mail(self):
        """retrieve emails from an IMAP server. For internal use.

        :rtype: list of :class:`OpenPGPMessage`
        """
        # XXX check `result` for OK?
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
        """retrieve emails

        :rtype: list of :class:`OpenPGPMessage`
        """
        if self.use_maildir:
            return self.get_maildir_mail()
        else:
            return self.get_imap_mail()

    def delete(self, message_id):
        """delete an email. Only works with IMAP

        :arg str message_id: the message ID of email to delete
        """
        if self.use_maildir:
            pass
        else:
            self.imap_mail.uid('store', message_id, '+FLAGS', '\\Deleted')

class EmailSender(object):
    """Encrypt, sign & send emails

    Creating an instance of this class **will send emails** by calling :meth:`construct_and_send_email`

    :ivar message: the *received* :class:`OpenPGPMessage` email
    :ivar env: Jinja template environment
    :ivar str fp: the fingerprint for the bot itself
    :ivar html_template: Jinja template for HTML part of response
    :ivar txt_template: Jinja template for HTML part of response
    ;ivar sender: function to actually send email. Defaults to self.send_email(self, msg_string, from_email, to_email)
    """
    # XXX rename fp to fingerprint

    def __init__(self, message, env, fp, sender=None):
        self.message = message
        self.env = env
        self.fp = fp
        if not sender:
            sender = self.send_email
        self.sender = sender

        self.html_template = self.env.get_template('email_template.html')
        self.txt_template = self.env.get_template('email_template.txt')

        self._gpg = GnuPG()

        self.construct_and_send_email()

    def as_string(self, msg):
        """convert message to a string. For internal use.

        :arg msg: :class:`OpenPGPMessage` to be stringified
        :rtype: str
        """
        # using this instead of msg.as_string(), because the header wrapping was causing sig verification problems
        # http://docs.python.org/2/library/email.message.html#email.message.Message.as_string
        fp = StringIO()
        g = Generator(fp, mangle_from_=False, maxheaderlen=0)
        g.flatten(msg)
        text = fp.getvalue()
        return text

    def construct_and_send_email(self):
        """Do work of constructing & sending reply email. For internal use."""
        # who to respond to?
        to_email = None
        if 'Reply-To' in self.message:
            to_email = self.message['Reply-To']
        elif 'From' in self.message:
            to_email = self.message['From']
        if not to_email:
            print 'Cannot decide who to respond to '
            return # XXX throw exception instead

        # what the response subject should be
        if 'Subject' in self.message:
            if self.message['Subject'][:4] != 'Re: ':
                subject = 'Re: '+self.message['Subject']
            else:
                subject = self.message['Subject']
        else:
            subject = 'CryptoBot response'

        from_email = '{0} <{1}>'.format(config.PGP_NAME, config.PGP_EMAIL)

        # start the email
        msg = MIMEMultipart('mixed')
        body = MIMEMultipart('alternative')

        template_vars = {
            'encrypted_right': self.message.encrypted_right,
            'encrypted_wrong': self.message.encrypted_wrong,
            'signed': self.message.signed,
            'pubkey_included': self.message.pubkey_included,
            'pubkey_included_wrong': self.message.pubkey_included_wrong,
            'pubkey_fingerprint': self.message.pubkey_fingerprint
        }

        body_txt = self.txt_template.render(template_vars)
        txt_part = MIMEBase('text', 'plain')
        txt_part.set_payload(body_txt)
        encode_quopri(txt_part)
        body.attach(txt_part)

        body_html = self.html_template.render(template_vars)
        html_part = MIMEBase('text', 'html')
        html_part.set_payload(body_html)
        encode_quopri(html_part)

        body.attach(html_part)
        msg.attach(body)

        # if the message is not encrypted, attach public key (#16)
        if not self.message.encrypted_right:
            pubkey = str(self._gpg.export_keys(self.fp))
            pubkey_filename = '{0} {1} (0x{2}) pub.asc'.format(config.PGP_NAME, config.PGP_EMAIL, str(self.fp)[:-8])

            pubkey_part = MIMEBase('application', 'pgp-keys')
            pubkey_part.add_header('Content-Disposition', 'attachment; filename="%s"' % pubkey_filename)
            pubkey_part.set_payload(pubkey)
            encode_quopri(pubkey_part)
            msg.attach(pubkey_part)

        # sign the message
        msg_string = (self.as_string(msg)+'\n').replace('\n', '\r\n')
        sig = self._gpg.sign(msg_string)

        # make a sig part
        sig_part = MIMEBase('application', 'pgp-signature', name='signature.asc')
        sig_part.add_header('Content-Description', 'OpenPGP digital signature')
        sig_part.add_header('Content-Disposition', 'attachment; filename="signature.asc"')
        sig_part.set_payload(sig)

        # wrap it all up in multipart/signed
        signed = MIMEMultipart(_subtype="signed", micalg="pgp-sha1", protocol="application/pgp-signature")
        signed.attach(msg)
        signed.attach(sig_part)

        # if we're just signing and not encrypting this message, add the headers directly to the signed part
        if not self.message.pubkey_fingerprint:
            signed['Subject'] = subject
            signed['From'] = from_email
            signed['To'] = to_email

        # need to add a '\r\n' right before the sig part (#19)
        # because of this bug http://bugs.python.org/issue14983
        signed_string = self.as_string(signed)
        i = signed_string.rfind('--', 0, signed_string.find('Content-Type: application/pgp-signature; name="signature.asc"'))
        signed_string = signed_string[0:i]+'\r\n'+signed_string[i:]

        # if we have a fingerprint to encrypt to, encrypt it
        if self.message.pubkey_fingerprint:
            # encrypt the message
            ciphertext = self._gpg.encrypt(signed_string, self.message.pubkey_fingerprint)

            # make an application/pgp-encrypted part
            encrypted = MIMEBase("application", "pgp-encrypted")
            encrypted.set_payload("Version: 1\r\n")

            # make application/octet-stream part
            octet_stream = MIMEBase("application", "octet-stream")
            octet_stream.set_payload(ciphertext)

            # make the multipart/encrypted wrapper
            wrapper = MIMEMultipart(_subtype="encrypted", protocol="application/pgp-encrypted")
            wrapper.attach(encrypted)
            wrapper.attach(octet_stream)

            # add headers to the encryption wrapper
            wrapper['Subject'] = subject
            wrapper['From'] = from_email
            wrapper['To'] = to_email

            final_message = self.as_string(wrapper)
        else:
            final_message = signed_string

        self.sender(final_message, from_email, to_email)
        print 'Responded to {0} {1}'.format(self.message['From'], str(template_vars))

    @staticmethod
    def send_email(msg_string, from_email, to_email):
        """Send email via SMTP. For internal use.

        :arg str msg_string: strigified reply email
        :arg str from_email: From: address
        :arg str to_email: To: address
        """
        if config.SMTP_SERVER == 'localhost':
            s = smtplib.SMTP(config.SMTP_SERVER)
        else:
            s = smtplib.SMTP_SSL(config.SMTP_SERVER)
            s.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)

        s.sendmail(from_email, [to_email], msg_string)
        s.quit()

    def sign_body(self):
        # need to implement PGP/MIME to sign the body here
        pass

    def encrypt_body(self):
        # need to implement PGP/MIME to sign the body here
        pass

class OpenPGPMessage(Message):
    """Email message with OpenPGP-specific properties"""

    def __init__(self, message, message_id=None, gpg=None):
        """
        :arg str message: raw text of the email
        :arg str message_id: IMAP message ID or maildir message path
        :arg gpg: :class:`GnuPG` instance or None (which will create one)
        """

        Message.__init__(self, message)
        self._message_id = message_id
        if not gpg:
            self._gpg = GnuPG()
        else:
            self._gpg = gpg

        self._content_types = ["text/plain", "text/html",
            "application/pgp-signature", "application/pgp-keys",
            "application/octet-stream"]

        self._parts = []
        for part in self.walk():
            content_type = part.get_content_type()
            if content_type in self._content_types:
                payload = quopri.decodestring(part.get_payload().strip())
                self._parts.append( (content_type, payload) )

        self._parse_for_openpgp()

    @property
    def message_id(self):
        """the message ID

        :type: str
        """
        return self._message_id

    def _find_email_payload_matches(self, payload_test):
        """find message parts containing a string

        :arg str payload_test: the string to search for
        :rtype: list
        :returns: matching message parts
        """
        matches = []
        for content_type, payload in self._parts:
            if content_type in self._content_types:
                if payload_test in payload:
                    matches.append(payload)
        return matches

    def _parse_for_openpgp(self):
        """parse email for PGP artifacts"""
        self._encrypted_right       = False
        self._encrypted_wrong       = False
        self._signed                = False
        self._pubkey_included       = False
        self._pubkey_included_wrong = False
        self._pubkey_fingerprint    = False

        encrypted_parts = self._find_email_payload_matches(PGP_ARMOR_HEADER_MESSAGE)
        if encrypted_parts:
            if len(encrypted_parts) > 1:
                # todo: raise error here?
                print "More than one encrypted part in this message. That's weird..."
            self._decrypted_text, signed = self._gpg.decrypt(encrypted_parts[0])
            if not self._decrypted_text:
                self._encrypted_wrong = True
            else:
                self._encrypted_right = True
                self._parts.append( ('text/plain', self._decrypted_text) )

                if signed:
                    self._signed = True

        signed_parts = self._find_email_payload_matches(PGP_ARMOR_HEADER_SIGNATURE)
        if signed_parts:
            if len(signed_parts) > 1:
                # todo: raise error here?
                print "More than one signed part in this message. That's weird..."
            self._signed = True
            # todo: check signature, public key attached, etc

        pubkey_parts = self._find_email_payload_matches(PGP_ARMOR_HEADER_PUBKEY)
        if pubkey_parts:
            # find all the pubkeys
            pubkeys = []
            for part in pubkey_parts:
                pubkeys += self._find_pubkeys(part)

            # does it look like there was an attempt at including a pubkey?
            if len(pubkeys) == 0 and PGP_ARMOR_HEADER_PUBKEY in part:
                self._pubkey_included_wrong = True

            # looks pubkey is included, try importing
            if len(pubkeys) > 0:
                fingerprints = []
                for pubkey in pubkeys:
                    fingerprint = self._gpg.import_keys(pubkey)
                    if fingerprint:
                        fingerprints.append(fingerprint)
                fingerprints = list(set(fingerprints))

                if len(fingerprints) == 0:
                    self._pubkey_included_wrong = True
                else:
                    # looks like we have a key, make sure there's a valid user id
                    name, email_addr = rfc822.parseaddr(self.get('From'))
                    valid_fingerprint = False
                    for fingerprint in fingerprints:
                        valid_uid = False
                        if self._gpg.has_public_key_with_uid(fingerprint, email_addr):
                            valid_uid = True

                        if valid_uid:
                            valid_fingerprint = fingerprint
                            break

                    if valid_fingerprint != False:
                        self._pubkey_included = True
                        self._pubkey_fingerprint = valid_fingerprint

    def _find_pubkeys(self, s):
        """find public key substrings

        :arg str s: the string to search in
        :rtype: list of str
        :returns: armored public keys
        """

        pubkeys = []

        in_block = False
        pubkey = ""
        for line in s.split('\n'):
            line = line.rstrip()
            if line == PGP_ARMOR_HEADER_PUBKEY:
                in_block = True
            if in_block:
                pubkey += line + "\n"
            if line == PGP_ARMOR_FOOTER_PUBKEY:
                in_block = False
                pubkeys.append(pubkey)
                pubkey = ""

        return pubkeys

    @property
    def encrypted_right(self):
        """is message encrypted correctly?

        :type: bool
        """
        return self._encrypted_right

    @property
    def encrypted_wrong(self):
        """is message encrypted incorrectly?

        :type: bool
        """
        return self._encrypted_wrong

    @property
    def signed(self):
        """is message signed?

        :type: bool
        """
        return self._signed

    @property
    def decrypted_text(self):
        return self._decrypted_text

    @property
    def pubkey_included(self):
        """is public key included in message?

        :type: bool
        """
        return self._pubkey_included

    @property
    def pubkey_included_wrong(self):
        """is public key incorrectly included in message?

        :type: bool
        """
        return self._pubkey_included_wrong

    @property
    def pubkey_fingerprint(self):
        """fingerprint of public key attached to message, or False if none found

        :type: str
        """
        return self._pubkey_fingerprint

def main(fp):
    """main entry point, sorta. Fetches & replies to emails, etc..

    :arg str fp: fingerprint of the bot itself
    """
    # XXX rename fp to fingerprint
    # jinja2
    template_loader = jinja2.FileSystemLoader(searchpath="templates")
    template_env = jinja2.Environment(loader=template_loader, trim_blocks=True)

    # email fetcher
    fetcher = EmailFetcher(use_maildir=config.USE_MAILDIR)
    messages = fetcher.get_all_mail()
    for message in messages:
        # respond to the email
        EmailSender(message, template_env, fp)

        # delete the email
        # (note: by default Gmail ignores the IMAP standard and archives email instead of deleting it
        #  http://gmailblog.blogspot.com/2008/10/new-in-labs-advanced-imap-controls.html )
        fetcher.delete(message.message_id)

def check_bot_keypair(allow_new_key):
    """Ensure the bot has a keypair, possibly creating a new one

    :arg bool allow_new_key: should new keypair be created if no existing one found
    :rtype: str
    :returns: fingerprint of the bot's keypair
    :raises: ValueError if no keypair found
    """
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

    fp = check_bot_keypair(args.allow_new_key)
    main(fp)
