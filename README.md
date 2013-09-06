OpenPGPBot
==========

## Getting Started

Start by copying `config_template.py` into `config.py` and editing it.

    $ cp config_template.py config.py

Set all of these settings:

- `PGP_NAME`: The name part of the user ID for for the bot's OpenPGP keypair
- `PGP_EMAIL`: The email part of the user ID for for the bot's OpenPGP keypair. This should be the email address that users are expected to email.
- `IMAP_SERVER`: The IMAP server to connect to, e.g. `imap.gmail.com`
- `IMAP_USERNAME`: The IMAP username
- `IMAP_PASSWORD`: The IMAP password

This is a Python project with some external dependencies. We recommend using
virtualenv:

    $ virtualenv env
    $ . env/bin/activate
    (env) $ pip install -r requirements.txt
    (env) $ ./bot.py
    # when you're done
    (env) $ deactivate

## Dev Notes

1. [OpenPGP RFC 4880](http://tools.ietf.org/html/rfc4880)
2. [MIME RFC 2045](http://tools.ietf.org/html/rfc2045)
3. [Helpful tutorial for Python's imaplib](http://yuji.wordpress.com/2011/06/22/python-imaplib-imap-example-with-gmail/)
