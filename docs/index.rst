.. image:: _static/ico-piston-typo.svg
   :width: 600 px
   :alt: alternate text
   :align: center

Piston - The Swiss army knife for the Steem network
===================================================


Piston is a tool with a library to interact with the STEEM network using Python 3.

* Piston's home is `github.com/xeroc/piston <https://github.com/xeroc/piston>`_ and
* this documentation is available through ReadMyDocs and is hosted on `piston.rocks <http://piston.rocks>`_

Piston.web - Graphical User Interface
-------------------------------------

(work in progress)

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
* accounts and private keys (with integrated wallet)
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
    contrib
    public-api
