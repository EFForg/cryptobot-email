# Getting Started With OpenPGP

Greetings, human. I'm glad you're interested in using `OpenPGP`! It's a difficult technology to master, so don't feel bad if it takes some time to learn.  Before we jump in, I'm going to start with a little bit of the history, termonology, and concepts behind `OpenPGP`. If you want, you can the Introduction section to get started immediately.

## Introduction

In 1991, Phil Zimmermann developed email encryption software called [Pretty Good Privacy](https://en.wikipedia.org/wiki/Pretty_Good_Privacy), or `PGP`, which he intended peace activists to use while organizing in the anti-nuclear movement. Today, PGP is a company that sells a proprietary encryption program by the same name. `OpenPGP` is the open protocol that defines how `PGP` encryption works, and `GnuPG` (`GPG` for short) is free software, and is 100% compatible with the proprietary version. `GPG` is much more popular than `PGP` today because it's free and open source. The terms `PGP`, `OpenPGP`, and `GPG` are often used interchangably.

Each person who wishes to send or receive encrypted email needs to generate their own pair of encryption keys, called a `keypair`. `PGP keypairs` are split into two parts, the `public key` and the `secret key`.

If you have someone's `public key`, you can do two things: **encrypt messages** that can only be decrypted with their `secret key`, and **verify signatures** that were generated with their `secret key`. It's safe to give your `public key` to anyone who wants it. The worst anyone can do with it is encrypt messages that only you can decrypt.

With your `secret key` you can do two things: **decrypt messages** that were encrypted using your `public key`, and **digitally sign messages**. It's important to keep your `secret key` secret. An attacker with your `secret key` can decrypt messages intended only for you, and he can forge messages on your behalf. `Secret keys` are generally encrypted with a `passphrase` (more on this below), so even if your computer gets compromised and your `secret key` gets stolen, the attacker would need to get your `passphrase` before he would have access to it.

If your `secret key` is compromised and the attacker has copies of any historical encrypted emails you have received, he can go back and retro-actively decrypt them all. This is not true of some other end-to-end encrypted technology such as `Off-the-Record` (`OTR`) chat encryption.

The security of crypto often relies on the security of a password. Since passwords are very easily guessed by computers, cryptographers prefer the term `passphrase` to encourage users to make their passwords very long and secure. For tips on choosing good `passphrases`, read the `passphrase` section of EFF's [Defending Privacy at the U.S. Border: A Guide for Travelers Carrying Digital Devices](https://www.eff.org/wp/defending-privacy-us-border-guide-travelers-carrying-digital-devices#passphrase) whitepaper, and also the [Diceware Passphrase Home Page](http://world.std.com/~reinhold/diceware.html).

Since you need other people's `public keys` in order to encrypt messages to them, `PGP` software lets you manage a `keyring` with your `secret key`, your `public key`, and all of the `public keys` of the people you communicate with.

Using `PGP` for email encryption can be very inconvenient. For example, if you set up `PGP` on your computer but have received an encrypted email on your phone, you won't be able to decrypt it to read the email until you get to your computer. However, if you use it correctly and keep your `secret key` from getting compromised, it works to keep the contents of your email private from everyone else, including the people who run your email server.

## Seting Up Your Computer for OpenPGP

The first step is installing the appropriate software. You need to download and install `GPG` on your computer, generate a `PGP keypair`, and install and configure an email client that supports `OpenPGP` integration. You can use `OpenPGP` with your Gmail or other webmail account, but you won't be able to use webmail for encrypting, decrypting, and verifying emails.

If you'd like to use `OpenPGP` with Gmail, [click here to configure your account first](gmail.md).

What operating system do you use?

* [Windows](/windows.md)
* [Mac OS X](/osx.md)
* [Linux](/linux.md) (Ubuntu, Debian, Fedora, etc.)
* [Tails](/tails.md)
