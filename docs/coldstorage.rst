***********
Coldstorage
***********

With release 0.3.2, piston now supports **offline signing** for
coldstorage. The procedure consists of three basic steps.

1. **preparation of the (unsigned) transaction**
2. **offline signing of the transaction**
3. **broadcasting of the signed transaction**

Let's go through the details real quick:

Preparation of the (unsigned) transaction
=========================================

Any transaction that piston can do (post, reply, edit, upvote, downvote,
transfer, powerup, powerdown, powerdownroute, convert, allow, disallow,
newaccount, updatememokey, etc.) can be generated **without** actually
signing them using the ``-x`` flag. The command will return a couple
lines (JSON format) and all you need to do is store those in a file and
carry them over to your offline computer.

**Important remark**: The default expiration time for transaction is
**30 seconds**. Apparently, nobody will be able to carry the transaction
to an offline computer, sign them and move them back to the online
computer within 30 seconds, you can increase the expiration to 5 minutes
by adding ``-e 300`` (300 seconds = 5 minutes)!

::

    $ piston -e 300 -x transfer fabian 0.1 SBD > unsigned-transaction.json

This gives you 5 minutes for your procedure. If you can't make it in 5
minutes, increase the ``300`` and try again.

Technical details
-----------------

A simple example looks like this:

::

    $ piston -x -e 300 transfer fabian 0.1 SBD
    {'expiration': '2016-09-07T08:17:19',
     'extensions': [],
     'operations': [['transfer',
                     {'amount': '0.100 SBD',
                      'from': 'xeroc',
                      'memo': '',
                      'to': 'fabian'}]],
     'ref_block_num': 38340,
     'ref_block_prefix': 336529008,
     'signatures': [],
     [...]
    }

That is the **basic** transaction and you see that the ``signatures``
are empty. In order to make it easier for the offline machine to sign
your transaction, there are a few more informations returned, namely:

::

    {
     [...]
     'missing_signatures': ['STM6quoHiVnmiDEXyz4fAsrNd28G6q7qBCitWbZGo4pTfQn8SwkzD',
                            'STM8HCf7QLUexogEviN8x1SpKRhFwg2sc8LrWuJqv7QsmWrua6ZyR'],
     'required_authorities': {'fabian': {'account_auths': [],
                                         'key_auths': [['STM8HCf7QLUexogEviN8x1SpKRhFwg2sc8LrWuJqv7QsmWrua6ZyR',
                                                        1]],
                                         'weight_threshold': 1},
                              'xeroc': {'account_auths': [['fabian', 1]],
                                        'key_auths': [['STM6quoHiVnmiDEXyz4fAsrNd28G6q7qBCitWbZGo4pTfQn8SwkzD',
                                                       1]],
                                        'weight_threshold': 2}},
    }

This data allows to identify the required keys without the need for an
internet connection (e.g. on you offline computer).

Offline Signing of the Transaction
==================================

With the unsigned transaction, you can go to your offline computer and
have it signed using your key there by using:

::

    piston sign --file unsigned-transaction.json > signed-transaction.json

The command will return the signed transaction which will look like
this:

::

    {'expiration': '2016-09-07T08:25:48',
     'extensions': [],
     'operations': [['transfer',
                     {'amount': '0.001 SBD',
                      'from': 'xeroc',
                      'memo': '',
                      'to': 'fabian'}]],
     'ref_block_num': 38510,
     'ref_block_prefix': 3441950962,
     'signatures': ['2071716bc5655d5327524004e33d340757cae067fcd30728484c21c605e26e3d0b548ca8b433af3037246084e67addbb726f45ef8d3fdb6e6b3e81415899bd762c']}

Carry this transaction to an internet connected computer and go to the
next step.

Broadcasting of the Signed Transaction
======================================

The signed transaction can easily be broadcast to the network/blockchain
by using

::

    piston broadcast --file signed-transaction.json

Unless you obtain an error, your transaction was transmitted to the
network and will shortly after be added to a block.

Congratulations!
