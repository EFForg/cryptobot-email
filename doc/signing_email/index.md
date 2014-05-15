---
title: How to Sign an Email
---

# How to Sign an Email

If you haven't read the [Getting Started](/getting_started/) guide, go read it now first.

It's important to digitally sign emails that you send so that people you email can confirm that you wrote them, and not from someone that's spoofing your email address or hacking into your email account. This is possible using PGP.

GnuPG generates PGP signatures by taking the email that you're about to send and using your secret key to a bunch of math. No one else can create same signature without having access to your secret key, but other people that have your public key are able to confirm that the signature was created by you.

In the end PGP signatures end up looking like this:

    -----BEGIN PGP SIGNATURE-----
    Version: GnuPG v1.4.14 (GNU/Linux)

    iQIcBAABAgAGBQJShRs7AAoJEAYb3vmMzaT6QJ4QAKn+6dDofIu/NqvuwDTYKZW6
    +kwUScIOItAaK4X0/LWQXyYUcMmPyEpSfiUGHSxEswLVyie7g28/CkwHY5bsokl5
    CuTQiqcIUEorE1RxAQo2RvrEOdsy+BSzJGMOqxRGaH5cUfZbps5qM8kWkmM0eO7+
    vFLRwjsqDq9I9y+ktiFthrMgf8akC6P9rA8pHCTTxaYdeKWaQdZbo83J2UQASZ3q
    XiJNR5ERVXRbENllcMUWngxGQd4jH5rxqHLDi1tso1wLKQEFfYUwSCYuNiHhoify
    vcsYZ2x0MKuKWuBrfqTfCxbfe1AkvcRBUPOzPs66WZB3PAULoHW79abEG1cA7KLK
    Of0R+U4wdpB87e7k+6ATRf7rLDzelJXbBLZCmdC0KymAY1lh+WjjABwDBfGzjPKF
    HNIEjs96Sx97FHoX7fQdGi0NjxX+myH7z/rOTqRkuPwu6qhy08yTbfCF7k2j8M2A
    /baZ3xdZ5HJC3vXzkGs4RjzycssH3nlizeaKXUaOSgkOERkx2dbML01Q+kpStrW6
    oSqUxFckCgBKdoO4ratznnOJT5D3h+UMB+X3BSdJXVSqNjXLjIS0YhOpjlAM2Nxd
    1MF4kvtcxW1EshQo7u8pLMw2uE8geRydeBVzsYe67YJXzWzakpxfEZKYfEq2lmSq
    MrqVKvp0sQjAQam3q5t2
    =5L2n
    -----END PGP SIGNATURE-----

But if you just tried adding this to the end of emails you write, it wouldn't work. If the person you sent this to tries to "verify" the signature using your public key, it would fail.

In this way, PGP signatures are much better than meatspace signatures. It's possible to generate a very realistic forgery of someone's written signature, but it's mathematically impossible to do the same with a cryptographic signature without having access to the secret key.

## Choose Your Operating System

What setup are you using? I'll explain how to sign your emails in the operating system of your choice:

* [Windows](windows.html)
* [Mac OS X](osx.html)
* [Linux](linux.html) (Ubuntu, Debian, Fedora, etc.)
* [Tails](tails.html)
