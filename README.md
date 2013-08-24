OpenPGPBot
==========

## Getting Started

This is a Python project with some external dependencies. We recommend using
virtualenv:

    $ virtualenv env
    $ . env/bin/activate
    (env) $ pip install -r requirements.txt
    (env) $ ./bot.py
    # when you're done
    (env) $ deactivate

At the moment, `bot.py` expects to find `config.py` with information about the
email server it is to talk to. Since `config.py` contains sensitive
authentication credentials, it is not included in this repo (it's in .gitignore
as well to prevent accidents). The easiest way to get going is to `cp
config_template.py` to `config.py` and fill in the appropriate values.

## Dev Notes

1. [OpenPGP RFC 4880](http://tools.ietf.org/html/rfc4880)
2. [MIME RFC 2045](http://tools.ietf.org/html/rfc2045)
3. [Helpful tutorial for Python's imaplib](http://yuji.wordpress.com/2011/06/22/python-imaplib-imap-example-with-gmail/)
