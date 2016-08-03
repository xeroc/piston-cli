# Welcome to piston.web

> The Swiss army knife for interacting with STEEM
>
> one of the most popular Steem apps
>
> crowdfunded, open source, secure, and constantly improving

Piston is a tool and a library to interact with the STEEM network using Python 3.

* Piston's home is [github.com/xeroc/piston](https://github.com/xeroc/piston) and
* Documentation is available through ReadMyDocs and is hosted on [piston.rocks](http://piston.rocks)
* Public [best effort](http://piston.readthedocs.io/en/develop/public-api.html) API available on [wss://this.piston.rocks](wss://this.piston.rocks)

## Piston.web

The interface you are currently looking at allows you to browse, read,
post and do mostly anything the Steem network allows you. Note that some
features are still under construction and that piston.web is improving
quickly.

## Command Line Tool

The command line tool that is bundled with this package is called ``piston`` and helps you

* browse,
* read,
* post,
* comment, and
* deal with your funds

in the Steem network. After installation, you can get the full list of features with:

    $ piston --help

## Library

Piston can be used as a library and thus helps you

* deal with configuration settings (node, prefered options, ..)
* accounts and private keys (with integrated wallet)
* presentation of Steem content

It further can be used to easily deploy bots on steem. The most easy
auto-reply bot can be coded with just a few lines of code:

```python
from piston.steem import Steem
steem = Steem(wif="<posting-key-for-default-author>")
for c in steem.stream_comments():
    if "Boobie" in c["body"]:
        print(c.reply(".. doobidoo"))
```
