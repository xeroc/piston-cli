# Piston for Steem

A command line tool to interface with the Steem network.

## Installation

### Install with `pip`:

```
pip3 install steem-piston
```

### Manual installation:

```
git clone https://github.com/xeroc/piston
cd piston 
python3 setup.py install --user
```

### Upgrade


```
$ pip install --user --upgrade steem-piston
```

## Usage

### Adding keys (for posting)

Piston comes with its own encrypted wallet to which keys need to be added:

    piston addkey <posting-wif-key>

On first run, you will be asked to provide a new passphrase that you
will need to provide every time you want to post on the Steem network.
If you chose an *empty* password, your keys will be stored in plain text
which allows automated posting but exposes your private key to your
local user.

### List available Keys and accounts

    piston listkeys

This command will give the list of public keys to which the private keys
are available.

    piston listaccounts

This command tries to resolve the public keys into account names registered
on the network (experimental).

### Posting

To post new content, you need to provide

* the author,
* a permlink, and
* a title

For posting the "posting-key" of the author needs to be added to the wallet.

Additionally, a `--category` can be added as well.

    echo "Texts" | piston.py post --author "<author>" --category "<category>" --title "<posttitle>" --permlink "<permlink>"
    cat filename | piston.py post --author "<author>" --category "<category>" --title "<posttitle>" --permlink "<permlink>"

### Replying

Here, the same parameters as for simply posting new content are
available except that instead of `--category` a `--replyto` has to be
provided to identify the post that you want the reply to be posted to.
The `--replyto` parameter takes the following form:

    @author/permlink

E.g:

    echo "Texts" | piston.py post --replyto "@xeroc/python-steem-0.1.1" --author "<author>" --title "<posttitle>" --permlink "<permlink>"
    cat filename | piston.py post --replyto "@xeroc/python-steem-0.1.1" --author "<author>" --title "<posttitle>" --permlink "<permlink>"
