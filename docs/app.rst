*****************
Piston Executable
*****************

Swiss army knife for interacting with the STEEM blockchain.

Quickstart
##########

You can start using piston by going throug out Steem hosted quickstart guide. Just run

::

    piston read @xeroc/piston-cli-quickstart

Available Commands
##################

Adding keys (for posting)
~~~~~~~~~~~~~~~~~~~~~~~~~

Piston comes with its own encrypted wallet to which keys need to be
added:

::

    piston addkey <posting-wif-key>

On first run, you will be asked to provide a new passphrase that you
will need to provide every time you want to post on the Steem network.
If you chose an *empty* password, your keys will be stored in plain text
which allows automated posting but exposes your private key to your
local user.

List available Keys and accounts
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

::

    piston listkeys

This command will give the list of public keys to which the private keys
are available.

::

    piston listaccounts

This command tries to resolve the public keys into account names
registered on the network (experimental).

Configuration
~~~~~~~~~~~~~

``piston`` comes with its owne configuration:

::

    piston set default_voter <account-name>
    piston set default_author <account-name>

All configuration variables are provided with ``piston set --help``
You can see your local configuration by calling

::

    piston config

Listing
~~~~~~~

``piston`` can list, sort, and filter for posts on the STEEM blockchain.
You can read about the parameters by

::

    piston list --help

Example:

::

    $ piston list --limit 3 --sort payout
    +----------------------------------------+------------------------------------------------+----------+---------+------------------+---------------+
    | identifier                             | title                                          | category | replies |            votes |       payouts |
    +----------------------------------------+------------------------------------------------+----------+---------+------------------+---------------+
    | @donaldtrump/lets-talk-politics        | Let's Talk Politics and the U.S. 2016 Election | politics |    20   | 1020791260074419 | 14106.752 SBD |
    | @nextgencrypto/steem-price-speculation | STEEM Price Speculation                        | steem    |    14   |  777027533714240 | 11675.872 SBD |
    | @clayop/lets-request-steem-to-poloniex | Let's Request STEEM to Poloniex                | steem    |    8    |  988929602909199 | 10530.426 SBD |
    +----------------------------------------+------------------------------------------------+----------+---------+------------------+---------------+

Reading
~~~~~~~

The subcommand ``read`` allows to read posts and replies from STEEM by
providing the post *identifier*. The identifier takes the form

::

    @author/permlink

The subcommands takes the optional parameters:

-  ``--full``: show the posts meta data as YAML formatted frontmatter
-  ``--comments``: to show all comments and replies made to that post
-  ``--parents x``: Show ``x`` parent posts

See examples:

::

    $ piston read "@xeroc/piston-readme"

    [this readme]

    $ piston read "@xeroc/python-steem-0-1" --comments

     ---
     author: puppies
     permlink: re-python-steem-0-1
     reply: '@puppies/re-python-steem-0-1'
     ---

     Great work Xeroc.  Your libraries make working with graphene chains truly a joy.
       ---
       author: xeroc
       permlink: re-puppies-re-python-stem-0-1
       reply: '@xeroc/re-puppies-re-python-stem-0-1'
       ---
       
       Thank you, I enjoy writing python a lot myself!
     ---
     author: dantheman
     permlink: re-xeroc-python-steem-0-1-20160414t145522693z
     reply: '@dantheman/re-xeroc-python-steem-0-1-20160414t145522693z'
     ---

     This is great work xeroc!  Thanks for supporting steem!

Categories
~~~~~~~~~~

Existing categories can be listed via:

::

    piston categories --limit 10

Please see the corresponding help page for further options:

::

    piston categories --help

Posting
~~~~~~~

To post new content, you need to provide

-  the author,
-  a permlink, and
-  a title

For posting the "posting-key" of the author needs to be added to the
wallet.

Additionally, a ``--category`` can be added as well.

::

    echo "Texts" | piston post --author "<author>" --category "<category>" --title "<posttitle>" --permlink "<permlink>"
    cat filename | piston post --author "<author>" --category "<category>" --title "<posttitle>" --permlink "<permlink>"

If you want to provide mulitple tags to your post, you can add it to the
frontmatter like this:

::

   ---
   author: ......
   category: .......
   title: .......
   tags:
     - introduceyourself
     - steemonsteroids
     - art
   ---

Replying
~~~~~~~~

Here, the same parameters as for simply posting new content are
available except that instead of ``--category`` a ``replyto`` has to be
provided to identify the post that you want the reply to be posted to.
The ``replyto`` parameter takes the following form:

::

    @author/permlink

E.g:

::

    echo "Texts" | piston reply --file - "@xeroc/python-steem-0.1.1" --author "<author>"
    cat filename | piston reply --file - "@xeroc/python-steem-0.1.1" --author "<author>"

If you want to use your favorit ``EDITOR``, you can do this by:

::

    piston reply "@xeroc/python-steem-0.1.1"

Editing
~~~~~~~

With piston, you can edit your own posts with your favorite text editor
(as defined in the environmental variable ``EDITOR``):

::

    $ piston "@xeroc/edit-test" 
    $ EDITOR="nano" piston "@xeroc/edit-test" 

If you want to replace your entire post and not *patch* it, you can add
the ``--replace`` flag.

Voting
~~~~~~

With ``piston``, you can up-/downvote any post with your installed
accounts:

::

    piston upvote --voter <voter> <identifier>
    piston downvote --voter <voter> <identifier>

providing the post *identifier*. The identifier takes the form

::

    @author/permlink

You can further define the weight (default 100%) manually with
``--weight``.

Replies
~~~~~~~

``piston`` can show replies to posts made by any author:

::

    piston replies --author xeroc

If ``--author`` is not provided, the *default* author as defined with
``piston set author`` will be taken. Further options are: ``--limit``.

Transfer Steem
~~~~~~~~~~~~~~

STEEM can be transfered via

::

    piston transfer receipient "100.000 STEEM"

If ``--author`` is not provided, the *default* account as defined with
``piston set author`` will be taken.

Powerup/Powerdown
~~~~~~~~~~~~~~~~~

You can powerup/down your account with piston using:

::

    piston powerup "100 STEEM"
    piston powerdown "10000 VESTS"

If ``--author``/``--to`` are not provided, the *default* account as defined with
``piston set author`` will be taken.

To route your powerdows to another account automatically, you can use
``powerdownroute``. Read more in the corresponding help::

   piston powerdownroute -h

Balances
~~~~~~~~

Get an account's balance with

::

    piston balance <account>

If ``<account>`` is not provided, the *default* account will be taken.

History
~~~~~~~

You can get an accounts history by using

::

    piston history <account>

Furthermore you can filter by ``types`` and limit the result by
transaction numer. More information can be found by calling ``piston
history -h`.
