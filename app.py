#!/usr/bin/env python

import config
import unsubscribe as unsub
from flask import Flask, render_template, request
app = Flask(__name__)
db = None

@app.route('/unsubscribe', methods=['GET', 'POST'])
def unsubscribe():
      if request.method == 'POST':
        email_address = request.form['email']
        if not db.find(email_address):
          db.add(email_address)
        return "%s unsubscribed!" % email_address
      else:
        return render_template('unsubscribe.html')

if __name__ == '__main__':
      db = unsub.getDatabase(config.DATABASE_URL)
      if db is None:
        print "Failed to connect to unsubscribe database url '%s'" % config.DATABASE_URL
        exit(1)
      app.run()
