# Using OpenPGP in Linux

Greetings, Linux users!

The first step is to install GnuPG, Thunderbird (an email client), and Enigmail (the GPG add-on for Thunderbird).

If you are using a Debian-based distribution such as Debian, Ubuntu, or Linux Mint, open a terminal and type these commands to make sure you have the right software installed:

    sudo apt-get install gnupg thunderbird enigmail

If you're using using a Red Hat-based distribution such as Red Hat or Fedora Core, open a terminal and run these commands:

    sudo yum install gnupg thunderbird thunderbird-enigmail

## Configuring Thunderbird

Now that you've installed Thunderbird, open it. You you will see the first run wizard. To set up your existing email address, click "Skip this and use my existing email". Then enter your name, email address, and the password to your email account.

![Thunderbird's Account Setup](../images/linux/thunderbird1.png)

If you use popular free email services like Gmail, Thunderbird should be able to automatically detect your email settings when you click Continue. If it doesn't, you may need to manually configure your IMAP and SMTP settings. In this case, Thunderbird auto-detected my email settings:

![Thunderbird's Account Setup, autodetected settings](../images/linux/thunderbird2.png)

After you're done configuring Thunderbird to check your email, click Done. Then click on "Inbox" in the top left to load your emails.

## Generate PGP Key

The next step is to generate a PGP key. Click the menu icon in the top-right and choose OpenPGP > Key Management.

![Open Key Management](../images/linux/thunderbird3.png)

When the Key Management window is open, select the Generate menu and choose New Key Pair.

![Open New Key Pair](../images/linux/thunderbird4.png)

From here you can generate a new PGP keypair. Type your passphrase twice. You can leave the comment blank. You can choose an expiration date as well. When you key expires you can always extend it.

![Generate Key](../images/linux/thunderbird5.png)

Before clicking the "Generate key" button, switch to the Advanced tab. Change the key size to 4096, which is the most secure PGP key that you can currently make.

![Generate Key - Advanced](../images/linux/thunderbird6.png)

If everything is correct, click the "Generate key" button. Enigmail will start generating your key. It shouldn't take more than a couple of minutes to finish.

When it's done, Enigmail will prompt you to create a revocation certificate. This is a file that you can use in the future to revoke your PGP key, in case you ever stop using it or it becomes compromised. Go ahead and create it, and store it somewhre safe.

![Revokation certificate](../images/linux/thunderbird7.png)

When it's done you'll see something like this. Yes, I agree that it's weird to see software this decade telling you to copy a file to a floppy disk.

![Revokation certificate](../images/linux/thunderbird8.png)

## Configure Enigmail


