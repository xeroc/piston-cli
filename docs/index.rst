Piston - The Swiss army knife for the Steem network
===================================================

Piston is a command line tool and library to interact with the STEEM network using Python 3.

Command Line Tool
-----------------

The command line tool that is bundled with this package is called ``piston`` and helps you

* browse,
* read,
* post,
* comment, and
* deal with your funds

in the Steem network. After installation, you can get the full list of features with::

    $ piston --help

Library
-------

Piston can be used as a library and thus helps you

* deal with configuration settings (node, prefered options, ..)
* accounts and private kes (with integrated wallet)
* presentation of Steem content

It further can be used to easily deploy bots on steem. The most easy
auto-reply bot can be coded with just a few lines of code:

.. code-block:: python

   from piston.steem import Steem
   import os
   import json
   steem = Steem(wif="<posting-key-for-default-author>")
   for c in steem.stream_comments():
       if "Boobie" in c["body"]:
           print(c.reply(".. doobidoo"))

Contents
========
.. toctree::
    :maxdepth: 2

    installation
    app
    lib
