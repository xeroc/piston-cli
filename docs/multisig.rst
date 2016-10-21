********
Multisig
********

Since the release of piston 0.3.3, you can use Steem's swiss
army knife for **multisig** transactions. This tutorial gives a brief
introduction and shows how it works. But first, let me clarify a few
technical terms:

What's a multisig transaction
=============================

The term *multisig* refers to the requirement of having **more than one
signature** to create a valid transaction. Most transactions don't have
this requirement because they are tied to **regular accounts**. However,
you can extend your account to a **multi-authority account** by adding
more keys and requiring more than one of them to sign a transaction. In
simple terms, you could secure your funds in such a way that you have
one access key stored on your computer and another stored on your mobile
phone. Then you can setup a scheme where you can only transfer funds
when both, your computer and your mobile phone sign the transaction.

What are "multi-authority" accounts
===================================

A multi-authority account does not consist of just a single access key
(e.g. password) but can consists of one or many

-  public keys (read: *passwords*) or
-  other account names.

This allows for some very cool setups for improved security and trust.
Let's say you have 2 friends and you want to setup a company together
with them. Then you create a new account remove the initial public keys
and put their account names into the authorities. Now you have an
account that is jointly owned by a group of people.

What are authorites and permissions?
====================================

On Steem, there are 3 permissions:

-  **active**: the active permission can move funds and trade in the
   internal exchange as well as change all permission authorities
   (except for the owner permission)
-  **posting**: the posting permission is required for posting and
   voting on Steem
-  **owner**: the owner permission is the super administrator and can
   change and overwrite all other permissions

All permissions have a threshold that needs to be reached by signatures.
Regular accounts have a threshold of one, such that only one access key
(*password*) is sufficient to access the account's permission.

Each permission can consist of one or multiple authorities and a weight
Two choices exist for the authorities:

-  a public key
-  an account name

and the weight is an integer number. The weight, together with the
threshold of the permission, works like this: If the sum of the weights
that are associated with the signatures exceed the threshold, the
transaction is valid.

For example: Let's say we take a look at the **active permission** of
account **xeroc**. We can take a look at its current permissions using
piston:

::

    $ piston permissions xeroc
    +------------+-----------+-----------------------------------------------------------+
    | Permission | Threshold |                                               Key/Account |
    +------------+-----------+-----------------------------------------------------------+
    |      owner |         2 |                                                fabian (1) |
    |            |           | STM7mgtsF5XPU9tokFpEz2zN9sQ89oAcRfcaSkZLsiqfWMtRDNKkc (1) |
    +------------+-----------+-----------------------------------------------------------+
    |     active |         2 |                                                fabian (1) |
    |            |           | STM6quoHiVnmiDEXyz4fAsrNd28G6q7qBCitWbZGo4pTfQn8SwkzD (1) |
    +------------+-----------+-----------------------------------------------------------+
    |    posting |         1 |                                             streemian (1) |
    |            |           | STM6xpuUdyoRkRJ1GQmrHeNiVC3KGadjrBayo25HaTyBxBCQNwG3j (1) |
    |            |           | STM8aJtoKdTsrRrWg3PB9XsbsCgZbVeDhQS3VUM1jkcXfVSjbv4T8 (1) |
    +------------+-----------+-----------------------------------------------------------+

We see that the threshold is *2* and there is one key and one account
with each having weight *1*. This means that we require a signature from
``STM6quoHiVnmiDEXyz4fAsrNd28G6q7qBCitWbZGo4pTfQn8SwkzD`` and from the
active key of ``fabian``. to construct a valid transaction that spends
from account ``xeroc``. And we will see below how that will work

Setting up a multisig account
=============================

So, in order to do multisig transactions, we first need a
multi-authority/multi-sig account. We can use piston to set this up.

**Remark**: Since we are changing permissions of accounts here, I
**highly** recommend to use this with a temporary account first and also
to use the ``-dx`` flag (nobroadcast) to verify the transaction before
broadcasting it.

**Recommendation**: We highly recommend to first test with the posting
or active permission and only if you feel comfortable, change the
*owner* permissions.

Adding an authority
-------------------

We can add a named account or a public key using ``piston allow``. We
need to define the affected account as well as the permission to modify.

::

    piston -dx allow --account xeroc --permission active fabian --weight 1
    piston -dx allow --account xeroc --permission active STM6quoHiVnmiDEXyz4fAsrNd28G6q7qBCitWbZGo4pTfQn8SwkzD --weight 1

These transaction will only add another authority to the permission with
the provided weight.

Adding an authority and changing the threshold
----------------------------------------------

To change the threshold of your account, you need to use the
``--threshold x`` parameter **with your last additional authority**.

::

    piston -dx allow --account xeroc --permission active dantheman --weight 1 --threshold 2

This will change the threshold.

Verify the multisig account
===========================

Using ``piston permissions`` we can take a look at the end result of our
actions:

::

    piston permissions <accountname>

Spending funds from a multisig account
======================================

Spending funds from a multisig account is as easy as `using piston for
coldstorage </piston/@xeroc/piston-howto-use-it-for-coldstorage>`__. The
major difference is that you need to transfer the **partially** signed
transaction between multiple parties.

**Note**: Due to the limitation of the expiration time to a maximum of
1h, you will need to find a time when you reach everyone within the
hour.

Create an unsigned transaction
------------------------------

Let's create an unsigned transaction using

::

    piston -x transfer --account xeroc fabian 0.001 SBD > unsigned-transaction.json

Send the ``unsigned-transaction.json`` file to all relevant parties and
let them sign the transaction

Signing unsigned/partially signed transactions
----------------------------------------------

The unsigned/partially signed transaction can be signed with the
available keys using

::

    piston sign --file unsigned-transaction.json

The result can be safely send to the initiator or be broadcasted if all
required transaction have been added.

Signing Party
-------------

Technically, it's your decision on how to collec the signatures. Either
you let them all **append** their signatures and forward the improved
partially signed transaction (assuming they know each others contact
data), or you let them send all the signed transactions back to you (if
only you know who has the keys). In the latter case you would need to
copy/paste the signatures into the transactions so that it takes the
form below and can then broadcast it.

::

    {'expiration': '2016-09-07T09:16:22',
     'extensions': [],
     'operations': [['transfer',
                     {'amount': '0.001 SBD',
                      'from': 'xeroc',
                      'memo': '',
                      'to': 'fabian'}]],
     'ref_block_num': 39520,
     'ref_block_prefix': 4016647731,
     'signatures': ['1f52fe34142a421ff711f0ddf29b0f782b74b68d9330380b464f44dbf59ab291b208f9969ec4bd215570b796e4f036d1a5ab37b84cdf2d9ad4d36162a799ebcd8f',
                    '1f1037cfe13b1f278fb2cae6b588dcd6a7d24de7ca26c29d1a7a70c4646b39d0d21c35749f444fb5b2686fd8552fe89b9013ab5723f1f4c5ba394c6e1a92ffb489',
                    '1f67430dd482848d14cfce7c5de11628b0cbea3cf3b0ced546b64172abb730cfed797da9490c66b2208d24d9ea24654b47e9ce758aa6f19b4bbb0dbd1cc1afe41c',
                    '20270dbcc95af22cc55404ff5b220a8aaf2585c3f47d496af1ae426c7d68f9e5c471d8dbc98c728bbeeec09dc8a47ddb58f3f55e67f5b603fdfd1ead47e8ffcb6a']}

Broadcasting the signed transactions
------------------------------------

Once the signatures are put together into one transactions, we can
broadcast the transaction using

::

    piston broadcast --file signed-transaction.json

The operation should (if the signatures are sufficient and valid) be
executed within seconds.

