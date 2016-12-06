import re
import json
import string
import random
from steemapi.steemnoderpc import SteemNodeRPC, NoAccessApi
from steembase.account import PrivateKey, PublicKey, Address
from steembase import memo
import steembase.transactions as transactions
from .utils import (
    resolveIdentifier,
    constructIdentifier,
    derivePermlink,
    formatTimeString
)
from .post import (
    Post,
    VotingInvalidOnArchivedPost
)
from .profile import Profile
from .wallet import Wallet
from .storage import configStorage as config
from .amount import Amount
from datetime import datetime, timedelta
from steemexchange.exchange import SteemExchange as SteemExchange
import logging
log = logging.getLogger(__name__)

prefix = "STM"
# prefix = "TST"

STEEMIT_100_PERCENT = 10000
STEEMIT_1_PERCENT = (STEEMIT_100_PERCENT / 100)


class AccountExistsException(Exception):
    pass


class AccountDoesNotExistsException(Exception):
    pass


class InsufficientAuthorityError(Exception):
    pass


class MissingKeyError(Exception):
    pass


class BroadcastingError(Exception):
    pass


class Steem(object):
    """ The purpose of this class it to simplify posting and dealing
        with accounts, posts and categories in Steem.

        The idea is to have a class that allows to do this:

        .. code-block:: python

            from piston.steem import Steem
            steem = Steem()
            steem.post("Testing piston-libs", "I am testing piston-libs", category="spam")

        All that is requires is for the user to have added a posting key with

        .. code-block:: bash

            piston addkey

        and setting a default author:

        .. code-block:: bash

            piston set default_author xeroc

        This class also deals with edits, votes and reading content.
    """

    wallet = None
    rpc = None

    def __init__(self,
                 node="",
                 rpcuser="",
                 rpcpassword="",
                 debug=False,
                 **kwargs):
        """ Connect to the Steem network.

            :param str node: Node to connect to *(optional)*
            :param str rpcuser: RPC user *(optional)*
            :param str rpcpassword: RPC password *(optional)*
            :param bool nobroadcast: Do **not** broadcast a transaction! *(optional)*
            :param bool debug: Enable Debugging *(optional)*
            :param array,dict,string keys: Predefine the wif keys to shortcut the wallet database
            :param bool offline: Boolean to prevent connecting to network (defaults to ``False``)

            Three wallet operation modes are possible:

            * **Wallet Database**: Here, piston loads the keys from the
              locally stored wallet SQLite database (see ``storage.py``).
              To use this mode, simply call ``Steem()`` without the
              ``keys`` parameter
            * **Providing Keys**: Here, you can provide the keys for
              your accounts manually. All you need to do is add the wif
              keys for the accounts you want to use as a simple array
              using the ``keys`` parameter to ``Steem()``.
            * **Force keys**: This more is for advanced users and
              requires that you know what you are doing. Here, the
              ``keys`` parameter is a dictionary that overwrite the
              ``active``, ``owner``, ``posting`` or ``memo`` keys for
              any account. This mode is only used for *foreign*
              signatures!

            If no node is provided, it will connect to the node of
            http://piston.rocks. It is **highly** recommended that you pick your own
            node instead. Default settings can be changed with:

            .. code-block:: python

                piston set node <host>

            where ``<host>`` starts with ``ws://`` or ``wss://``.
        """
        # More specific set of APIs to register to
        if "apis" not in kwargs:
            kwargs["apis"] = [
                "database",
                "network_broadcast",
                "account_by_key_api"
            ]

        if not kwargs.pop("offline", False):
            self._connect(node=node,
                          rpcuser=rpcuser,
                          rpcpassword=rpcpassword,
                          **kwargs)

        self.debug = debug
        self.nobroadcast = kwargs.get("nobroadcast", False)
        self.unsigned = kwargs.pop("unsigned", False)
        self.expiration = int(kwargs.pop("expires", 30))

        # Compatibility after name change from wif->keys
        if "wif" in kwargs and "keys" not in kwargs:
            kwargs["keys"] = kwargs["wif"]

        if "keys" in kwargs:
            self.wallet = Wallet(self.rpc, keys=kwargs["keys"])
        else:
            self.wallet = Wallet(self.rpc)

    def _connect(self,
                 node="",
                 rpcuser="",
                 rpcpassword="",
                 **kwargs):
        """ Connect to Steem network (internal use only)
        """
        if not node:
            if "node" in config:
                node = config["node"]
            else:
                raise ValueError("A Steem node needs to be provided!")

        if not rpcuser and "rpcuser" in config:
            rpcuser = config["rpcuser"]

        if not rpcpassword and "rpcpassword" in config:
            rpcpassword = config["rpcpassword"]

        self.rpc = SteemNodeRPC(node, rpcuser, rpcpassword, **kwargs)

    def _addUnsignedTxParameters(self, tx, account, permission):
        """ This is a private method that adds side information to a
            unsigned/partial transaction in order to simplify later
            signing (e.g. for multisig or coldstorage)
        """
        accountObj = self.rpc.get_account(account)
        if not accountObj:
            raise AccountDoesNotExistsException(accountObj)
        authority = accountObj.get(permission)
        # We add a required_authorities to be able to identify
        # how to sign later. This is an array, because we
        # may later want to allow multiple operations per tx
        tx.update({"required_authorities": {
            account: authority
        }})
        for account_auth in authority["account_auths"]:
            account_auth_account = self.rpc.get_account(account_auth[0])
            if not account_auth_account:
                raise AccountDoesNotExistsException(account_auth_account)
            tx["required_authorities"].update({
                account_auth[0]: account_auth_account.get(permission)
            })

        # Try to resolve required signatures for offline signing
        tx["missing_signatures"] = [
            x[0] for x in authority["key_auths"]
        ]
        # Add one recursion of keys from account_auths:
        for account_auth in authority["account_auths"]:
            account_auth_account = self.rpc.get_account(account_auth[0])
            if not account_auth_account:
                raise AccountDoesNotExistsException(account_auth_account)
            tx["missing_signatures"].extend(
                [x[0] for x in account_auth_account[permission]["key_auths"]]
            )
        return tx

    def finalizeOp(self, op, account, permission):
        """ This method obtains the required private keys if present in
            the wallet, finalizes the transaction, signs it and
            broadacasts it

            :param operation op: The operation to broadcast
            :param operation account: The account that authorizes the
                operation
            :param string permission: The required permission for
                signing (active, owner, posting)
        """
        if self.unsigned:
            tx = self.constructTx(op, None)
            return self._addUnsignedTxParameters(tx, account, permission)
        else:
            if permission == "active":
                wif = self.wallet.getActiveKeyForAccount(account)
            elif permission == "posting":
                wif = self.wallet.getPostingKeyForAccount(account)
            elif permission == "owner":
                wif = self.wallet.getOwnerKeyForAccount(account)
            else:
                raise ValueError("Invalid permission")
            tx = self.constructTx(op, wif)
            return self.broadcast(tx)

    def constructTx(self, op, wifs=[]):
        """ Execute an operation by signing it with the ``wif`` key

            :param Object op: The operation to be signed and broadcasts as
                              provided by the ``transactions`` class.
            :param string wifs: One or many wif keys to use for signing
                                a transaction
        """
        if not isinstance(wifs, list):
            wifs = [wifs]

        if not any(wifs) and not self.unsigned:
            raise MissingKeyError

        ops = [transactions.Operation(op)]
        expiration = transactions.formatTimeFromNow(self.expiration)
        ref_block_num, ref_block_prefix = transactions.getBlockParams(self.rpc)
        tx = transactions.Signed_Transaction(
            ref_block_num=ref_block_num,
            ref_block_prefix=ref_block_prefix,
            expiration=expiration,
            operations=ops
        )
        if not self.unsigned:
            tx = tx.sign(wifs)

        tx = tx.json()

        if self.debug:
            log.debug(str(tx))

        return tx

    def sign(self, tx, wifs=[]):
        """ Sign a provided transaction witht he provided key(s)

            :param dict tx: The transaction to be signed and returned
            :param string wifs: One or many wif keys to use for signing
                a transaction. If not present, the keys will be loaded
                from the wallet as defined in "missing_signatures" key
                of the transactions.
        """
        if not isinstance(wifs, list):
            wifs = [wifs]

        if not isinstance(tx, dict):
            raise ValueError("Invalid Transaction Format")

        if not any(wifs):
            missing_signatures = tx.get("missing_signatures", [])
            for pub in missing_signatures:
                wif = self.wallet.getPrivateKeyForPublicKey(pub)
                if wif:
                    wifs.append(wif)
        try:
            signedtx = transactions.Signed_Transaction(**tx)
        except:
            raise ValueError("Invalid Transaction Format")

        signedtx.sign(wifs)
        tx["signatures"].extend(signedtx.json().get("signatures"))

        return tx

    def broadcast(self, tx):
        """ Broadcast a transaction to the Steem network

            :param tx tx: Signed transaction to broadcast
        """
        if self.nobroadcast:
            log.warning("Not broadcasting anything!")
            return tx

        try:
            if not self.rpc.verify_authority(tx):
                raise InsufficientAuthorityError
        except:
            raise InsufficientAuthorityError

        try:
            self.rpc.broadcast_transaction(tx, api="network_broadcast")
        except:
            raise BroadcastingError

        return tx

    def info(self):
        """ Returns the global properties
        """
        return self.rpc.get_dynamic_global_properties()

    def reply(self, identifier, body, title="", author="", meta=None):
        """ Reply to an existing post

            :param str identifier: Identifier of the post to reply to. Takes the
                             form ``@author/permlink``
            :param str body: Body of the reply
            :param str title: Title of the reply post
            :param str author: Author of reply (optional) if not provided
                               ``default_user`` will be used, if present, else
                               a ``ValueError`` will be raised.
            :param json meta: JSON meta object that can be attached to the
                              post. (optional)
        """
        return self.post(title,
                         body,
                         meta=meta,
                         author=author,
                         reply_identifier=identifier)

    def edit(self,
             identifier,
             body,
             meta={},
             replace=False):
        """ Edit an existing post

            :param str identifier: Identifier of the post to reply to. Takes the
                             form ``@author/permlink``
            :param str body: Body of the reply
            :param json meta: JSON meta object that can be attached to the
                              post. (optional)
            :param bool replace: Instead of calculating a *diff*, replace
                                 the post entirely (defaults to ``False``)
        """
        post_author, post_permlink = resolveIdentifier(identifier)
        original_post = self.rpc.get_content(post_author, post_permlink)

        if replace:
            newbody = body
        else:
            import diff_match_patch
            dmp = diff_match_patch.diff_match_patch()
            patch = dmp.patch_make(original_post["body"], body)
            newbody = dmp.patch_toText(patch)

            if not newbody:
                log.info("No changes made! Skipping ...")
                return

        reply_identifier = constructIdentifier(
            original_post["parent_author"],
            original_post["parent_permlink"]
        )

        new_meta = {}
        if meta:
            if original_post["json_metadata"]:
                import json
                new_meta = json.loads(original_post["json_metadata"]).update(meta)
            else:
                new_meta = meta

        return self.post(
            original_post["title"],
            newbody,
            reply_identifier=reply_identifier,
            author=original_post["author"],
            permlink=original_post["permlink"],
            meta=new_meta,
        )

    def post(self,
             title,
             body,
             author=None,
             permlink=None,
             meta={},
             reply_identifier=None,
             category=None,
             tags=[]):
        """ New post

            :param str title: Title of the reply post
            :param str body: Body of the reply
            :param str author: Author of reply (optional) if not provided
                               ``default_user`` will be used, if present, else
                               a ``ValueError`` will be raised.
            :param json meta: JSON meta object that can be attached to the
                              post.
            :param str reply_identifier: Identifier of the post to reply to. Takes the
                                         form ``@author/permlink``
            :param str category: (deprecated, see ``tags``) Allows to
                define a category for new posts.  It is highly recommended
                to provide a category as posts end up in ``spam`` otherwise.
                If no category is provided but ``tags``, then the first tag
                will be used as category
            :param array tags: The tags to flag the post with. If no
                category is used, then the first tag will be used as
                category
        """

        if not author and config["default_author"]:
            author = config["default_author"]

        if not author:
            raise ValueError(
                "Please define an author. (Try 'piston set default_author'"
            )

        if not isinstance(meta, dict):
            try:
                meta = json.loads(meta)
            except:
                meta = {}
        if isinstance(tags, str):
            tags = list(filter(None, (re.split("[\W_]", tags))))
        if not category and tags:
            # extract the first tag
            category = tags[0]
            tags = list(set(tags))
            # do not use the first tag in tags
            meta.update({"tags": tags[1:]})
        elif tags:
            # store everything in tags
            tags = list(set(tags))
            meta.update({"tags": tags})

        if reply_identifier and not category:
            parent_author, parent_permlink = resolveIdentifier(reply_identifier)
            if not permlink :
                permlink = derivePermlink(title, parent_permlink)
        elif category and not reply_identifier:
            parent_permlink = derivePermlink(category)
            parent_author = ""
            if not permlink :
                permlink = derivePermlink(title)
        elif not category and not reply_identifier:
            parent_author = ""
            parent_permlink = ""
            if not permlink :
                permlink = derivePermlink(title)
        else:
            raise ValueError(
                "You can't provide a category while replying to a post"
            )

        op = transactions.Comment(
            **{"parent_author": parent_author,
               "parent_permlink": parent_permlink,
               "author": author,
               "permlink": permlink,
               "title": title,
               "body": body,
               "json_metadata": meta}
        )

        return self.finalizeOp(op, author, "posting")

    def vote(self,
             identifier,
             weight,
             voter=None):
        """ Vote for a post

            :param str identifier: Identifier for the post to upvote Takes
                                   the form ``@author/permlink``
            :param float weight: Voting weight. Range: -100.0 - +100.0. May
                                 not be 0.0
            :param str voter: Voter to use for voting. (Optional)

            If ``voter`` is not defines, the ``default_voter`` will be taken or
            a ValueError will be raised

            .. code-block:: python

                piston set default_voter <account>
        """
        if not voter:
            if "default_voter" in config:
                voter = config["default_voter"]
        if not voter:
            raise ValueError("You need to provide a voter account")

        post_author, post_permlink = resolveIdentifier(identifier)

        op = transactions.Vote(
            **{"voter": voter,
               "author": post_author,
               "permlink": post_permlink,
               "weight": int(weight * STEEMIT_1_PERCENT)}
        )

        return self.finalizeOp(op, voter, "posting")

    def create_account(self,
                       account_name,
                       json_meta={},
                       creator=None,
                       owner_key=None,
                       active_key=None,
                       posting_key=None,
                       memo_key=None,
                       password=None,
                       additional_owner_keys=[],
                       additional_active_keys=[],
                       additional_posting_keys=[],
                       additional_owner_accounts=[],
                       additional_active_accounts=[],
                       additional_posting_accounts=[],
                       storekeys=True,
                       ):
        """ Create new account in Steem

            The brainkey/password can be used to recover all generated keys (see
            `steembase.account` for more details.

            By default, this call will use ``default_author`` to
            register a new name ``account_name`` with all keys being
            derived from a new brain key that will be returned. The
            corresponding keys will automatically be installed in the
            wallet.

            .. note:: Account creations cost a fee that is defined by
                       the network. If you create an account, you will
                       need to pay for that fee!

            .. warning:: Don't call this method unless you know what
                          you are doing! Be sure to understand what this
                          method does and where to find the private keys
                          for your account.

            .. note:: Please note that this imports private keys
                      (if password is present) into the wallet by
                      default. However, it **does not import the owner
                      key** for security reasons. Do NOT expect to be
                      able to recover it from piston if you lose your
                      password!

            :param str account_name: (**required**) new account name
            :param str json_meta: Optional meta data for the account
            :param str creator: which account should pay the registration fee
                                (defaults to ``default_author``)
            :param str owner_key: Main owner key
            :param str active_key: Main active key
            :param str posting_key: Main posting key
            :param str memo_key: Main memo_key
            :param str password: Alternatively to providing keys, one
                                 can provide a password from which the
                                 keys will be derived
            :param array additional_owner_keys:  Additional owner public keys
            :param array additional_active_keys: Additional active public keys
            :param array additional_posting_keys: Additional posting public keys
            :param array additional_owner_accounts: Additional owner account names
            :param array additional_active_accounts: Additional acctive account names
            :param array additional_posting_accounts: Additional posting account names
            :param bool storekeys: Store new keys in the wallet (default: ``True``)
            :raises AccountExistsException: if the account already exists on the blockchain

        """
        if not creator and config["default_author"]:
            creator = config["default_author"]
        if not creator:
            raise ValueError(
                "Not creator account given. Define it with " +
                "creator=x, or set the default_author in piston")
        if password and (owner_key or posting_key or active_key or memo_key):
            raise ValueError(
                "You cannot use 'password' AND provide keys!"
            )

        account = None
        try:
            account = self.rpc.get_account(account_name)
        except:
            pass
        if account:
            raise AccountExistsException

        " Generate new keys from password"
        from steembase.account import PasswordKey, PublicKey
        if password:
            posting_key = PasswordKey(account_name, password, role="posting")
            active_key  = PasswordKey(account_name, password, role="active")
            owner_key   = PasswordKey(account_name, password, role="owner")
            memo_key    = PasswordKey(account_name, password, role="memo")
            posting_pubkey = posting_key.get_public_key()
            active_pubkey  = active_key.get_public_key()
            owner_pubkey   = owner_key.get_public_key()
            memo_pubkey    = memo_key.get_public_key()
            posting_privkey = posting_key.get_private_key()
            active_privkey  = active_key.get_private_key()
            # owner_privkey   = owner_key.get_private_key()
            memo_privkey    = memo_key.get_private_key()
            # store private keys
            if storekeys:
                # self.wallet.addPrivateKey(owner_privkey)
                self.wallet.addPrivateKey(active_privkey)
                self.wallet.addPrivateKey(posting_privkey)
                self.wallet.addPrivateKey(memo_privkey)
        elif (owner_key and posting_key and active_key and memo_key):
            posting_pubkey = PublicKey(posting_key, prefix=prefix)
            active_pubkey  = PublicKey(active_key, prefix=prefix)
            owner_pubkey   = PublicKey(owner_key, prefix=prefix)
            memo_pubkey    = PublicKey(memo_key, prefix=prefix)
        else:
            raise ValueError(
                "Call incomplete! Provide either a password or public keys!"
            )

        owner   = format(owner_pubkey, prefix)
        active  = format(active_pubkey, prefix)
        posting = format(posting_pubkey, prefix)
        memo    = format(memo_pubkey, prefix)

        owner_key_authority = [[owner, 1]]
        active_key_authority = [[active, 1]]
        posting_key_authority = [[posting, 1]]
        owner_accounts_authority = []
        active_accounts_authority = []
        posting_accounts_authority = []

        # additional authorities
        for k in additional_owner_keys:
            owner_key_authority.append([k, 1])
        for k in additional_active_keys:
            active_key_authority.append([k, 1])
        for k in additional_posting_keys:
            posting_key_authority.append([k, 1])

        for k in additional_owner_accounts:
            owner_accounts_authority.append([k, 1])
        for k in additional_active_accounts:
            active_accounts_authority.append([k, 1])
        for k in additional_posting_accounts:
            posting_accounts_authority.append([k, 1])

        props = self.rpc.get_chain_properties()
        fee = props["account_creation_fee"]
        s = {'creator': creator,
             'fee': fee,
             'json_metadata': json_meta,
             'memo_key': memo,
             'new_account_name': account_name,
             'owner': {'account_auths': owner_accounts_authority,
                       'key_auths': owner_key_authority,
                       'weight_threshold': 1},
             'active': {'account_auths': active_accounts_authority,
                        'key_auths': active_key_authority,
                        'weight_threshold': 1},
             'posting': {'account_auths': posting_accounts_authority,
                         'key_auths': posting_key_authority,
                         'weight_threshold': 1}}
        op = transactions.Account_create(**s)

        return self.finalizeOp(op, creator, "active")

    def transfer(self, to, amount, asset, memo="", account=None):
        """ Transfer SBD or STEEM to another account.

            :param str to: Recipient
            :param float amount: Amount to transfer
            :param str asset: Asset to transfer (``SBD`` or ``STEEM``)
            :param str memo: (optional) Memo, may begin with `#` for encrypted messaging
            :param str account: (optional) the source account for the transfer if not ``default_account``
        """
        if not account:
            if "default_account" in config:
                account = config["default_account"]
        if not account:
            raise ValueError("You need to provide an account")

        assert asset == "SBD" or asset == "STEEM"

        if memo and memo[0] == "#":
            from steembase import memo as Memo
            memo_wif = self.wallet.getMemoKeyForAccount(account)
            if not memo_wif:
                raise MissingKeyError("Memo key for %s missing!" % account)
            to_account = self.rpc.get_account(to)
            if not to_account:
                raise AccountDoesNotExistsException(to_account)
            nonce = str(random.getrandbits(64))
            memo = Memo.encode_memo(
                PrivateKey(memo_wif),
                PublicKey(to_account["memo_key"], prefix=prefix),
                nonce,
                memo
            )

        op = transactions.Transfer(
            **{"from": account,
               "to": to,
               "amount": '{:.{prec}f} {asset}'.format(
                   float(amount),
                   prec=3,
                   asset=asset
               ),
               "memo": memo
               }
        )
        return self.finalizeOp(op, account, "active")

    def withdraw_vesting(self, amount, account=None):
        """ Withdraw VESTS from the vesting account.

            :param float amount: number of VESTS to withdraw over a period of 104 weeks
            :param str account: (optional) the source account for the transfer if not ``default_account``
        """
        if not account:
            if "default_account" in config:
                account = config["default_account"]
        if not account:
            raise ValueError("You need to provide an account")

        op = transactions.Withdraw_vesting(
            **{"account": account,
               "vesting_shares": '{:.{prec}f} {asset}'.format(
                   float(amount),
                   prec=6,
                   asset="VESTS"
               ),
               }
        )

        return self.finalizeOp(op, account, "active")

    def transfer_to_vesting(self, amount, to=None, account=None):
        """ Vest STEEM

            :param float amount: number of STEEM to vest
            :param str to: (optional) the source account for the transfer if not ``default_account``
            :param str account: (optional) the source account for the transfer if not ``default_account``
        """
        if not account:
            if "default_account" in config:
                account = config["default_account"]
        if not account:
            raise ValueError("You need to provide an account")

        if not to:
            to = account  # powerup on the same account

        op = transactions.Transfer_to_vesting(
            **{"from": account,
               "to": to,
               "amount": '{:.{prec}f} {asset}'.format(
                   float(amount),
                   prec=3,
                   asset="STEEM")
               }
        )

        return self.finalizeOp(op, account, "active")

    def convert(self, amount, account=None, requestid=None):
        """ Convert SteemDollars to Steem (takes one week to settle)

            :param float amount: number of VESTS to withdraw over a period of 104 weeks
            :param str account: (optional) the source account for the transfer if not ``default_account``
        """
        if not account and "default_account" in config:
            account = config["default_account"]
        if not account:
            raise ValueError("You need to provide an account")

        if requestid:
            requestid = int(requestid)
        else:
            requestid = random.getrandbits(32)
        op = transactions.Convert(
            **{"owner": account,
               "requestid": requestid,
               "amount": '{:.{prec}f} {asset}'.format(
                   float(amount),
                   prec=3,
                   asset="SBD"
               )}
        )

        return self.finalizeOp(op, account, "active")

    def get_content(self, identifier):
        """ Get the full content of a post.

            :param str identifier: Identifier for the post to upvote Takes
                                   the form ``@author/permlink``
        """
        return Post(self, identifier)

    def get_recommended(self, user):
        """ (obsolete) Get recommended posts for user
        """
        log.critical("get_recommended has been removed from the backend.")
        return []

    def get_blog(self, user):
        """ Get blog posts of a user

            :param str user: Show recommendations for this author
        """
        state = self.rpc.get_state("/@%s/blog" % user)
        posts = state["accounts"][user].get("blog", [])
        r = []
        for p in posts:
            post = state["content"][p]
            r.append(Post(self, post))
        return r

    def get_replies(self, author, skipown=True):
        """ Get replies for an author

            :param str author: Show replies for this author
            :param bool skipown: Do not show my own replies
        """
        state = self.rpc.get_state("/@%s/recent-replies" % author)
        replies = state["accounts"][author].get("recent_replies", [])
        discussions  = []
        for reply in replies:
            post = state["content"][reply]
            if skipown and post["author"] == author:
                continue
            discussions.append(Post(self, post))
        return discussions

    def get_promoted(self):
        """ Get promoted posts
        """
        state = self.rpc.get_state("/promoted")
        # why is there a empty key in the struct?
        promoted = state["discussion_idx"][''].get("promoted", [])
        r = []
        for p in promoted:
            post = state["content"].get(p)
            r.append(Post(self, post))
        return r

    def get_posts(self, limit=10,
                  sort="hot",
                  category=None,
                  start=None):
        """ Get multiple posts in an array.

            :param int limit: Limit the list of posts by ``limit``
            :param str sort: Sort the list by "recent" or "payout"
            :param str category: Only show posts in this category
            :param str start: Show posts after this post. Takes an
                              identifier of the form ``@author/permlink``
        """

        discussion_query = {"tag": category,
                            "limit": limit,
                            }
        if start:
            author, permlink = resolveIdentifier(start)
            discussion_query["start_author"] = author
            discussion_query["start_permlink"] = permlink

        if sort not in ["trending", "created", "active", "cashout",
                        "payout", "votes", "children", "hot"]:
            raise Exception("Invalid choice of '--sort'!")
            return

        func = getattr(self.rpc, "get_discussions_by_%s" % sort)
        r = []
        for p in func(discussion_query):
            r.append(Post(self, p))
        return r

    def get_comments(self, identifier):
        """ Return **first-level** comments of a post.

            :param str identifier: Identifier of a post. Takes an
                                   identifier of the form ``@author/permlink``
        """
        post_author, post_permlink = resolveIdentifier(identifier)
        posts = self.rpc.get_content_replies(post_author, post_permlink)
        r = []
        for post in posts:
            r.append(Post(self, post))
        return(r)

    def get_categories(self, sort="trending", begin=None, limit=10):
        """ List categories

            :param str sort: Sort categories by "trending", "best",
                             "active", or "recent"
            :param str begin: Show categories after this
                              identifier of the form ``@author/permlink``
            :param int limit: Limit categories by ``x``
        """
        if sort == "trending":
            func = self.rpc.get_trending_categories
        elif sort == "best":
            func = self.rpc.get_best_categories
        elif sort == "active":
            func = self.rpc.get_active_categories
        elif sort == "recent":
            func = self.rpc.get_recent_categories
        else:
            log.error("Invalid choice of '--sort' (%s)!" % sort)
            return

        return func(begin, limit)

    def get_balances(self, account=None):
        """ Get the balance of an account

            :param str account: (optional) the source account for the transfer if not ``default_account``
        """
        if not account:
            if "default_account" in config:
                account = config["default_account"]
        if not account:
            raise ValueError("You need to provide an account")
        a = self.rpc.get_account(account)
        if not a:
            raise AccountDoesNotExistsException(account)
        info = self.rpc.get_dynamic_global_properties()
        steem_per_mvest = (
            Amount(info["total_vesting_fund_steem"]).amount /
            (Amount(info["total_vesting_shares"]).amount / 1e6)
        )
        vesting_shares_steem = "%f STEEM" % (Amount(a["vesting_shares"]).amount / 1e6 * steem_per_mvest)
        return {
            "balance": Amount(a["balance"]),
            "vesting_shares" : Amount(a["vesting_shares"]),
            "sbd_balance": Amount(a["sbd_balance"]),
            "savings_balance": Amount(a["savings_balance"]),
            "savings_sbd_balance": Amount(a["savings_sbd_balance"]),
            # computed amounts
            "vesting_shares_steem" : Amount(vesting_shares_steem),
        }

    def get_account_history(self, *args, **kwargs):
        return self.rpc.account_history(*args, **kwargs)

    def decode_memo(self, enc_memo, account):
        """ Try to decode an encrypted memo
        """
        assert enc_memo[0] == "#", "decode memo requires memos to start with '#'"
        keys = memo.involved_keys(enc_memo)
        wif = None
        for key in keys:
            wif = self.wallet.getPrivateKeyForPublicKey(str(key))
            if wif:
                break
        if not wif:
            raise MissingKeyError
        return memo.decode_memo(PrivateKey(wif), enc_memo)

    def stream_comments(self, *args, **kwargs):
        """ Generator that yields posts when they come in

            To be used in a for loop that returns an instance of `Post()`.
        """
        for c in self.rpc.stream("comment", *args, **kwargs):
            yield Post(self, c)

    def interest(self, account):
        """ Caluclate interest for an account

            :param str account: Account name to get interest for
        """
        account = self.rpc.get_account(account)
        if not account:
            raise AccountDoesNotExistsException(account)
        last_payment = formatTimeString(account["sbd_last_interest_payment"])
        next_payment = last_payment + timedelta(days=30)
        interest_rate = self.info()["sbd_interest_rate"] / 100  # the result is in percent!
        interest_amount = (interest_rate / 100) * int(
            int(account["sbd_seconds"]) / (60 * 60 * 24 * 356)
        ) * 10 ** -3

        return {
            "interest": interest_amount,
            "last_payment" : last_payment,
            "next_payment" : next_payment,
            "next_payment_duration" : next_payment - datetime.now(),
            "interest_rate": interest_rate,
        }

    def set_withdraw_vesting_route(self, to, percentage=100,
                                   account=None, auto_vest=False):
        """ Set up a vesting withdraw route. When vesting shares are
            withdrawn, they will be routed to these accounts based on the
            specified weights.

            :param str to: Recipient of the vesting withdrawal
            :param float percentage: The percent of the withdraw to go
                to the 'to' account.
            :param str account: (optional) the vesting account
            :param bool auto_vest: Set to true if the from account
                should receive the VESTS as VESTS, or false if it should
                receive them as STEEM. (defaults to ``False``)
        """
        if not account:
            if "default_account" in config:
                account = config["default_account"]
        if not account:
            raise ValueError("You need to provide an account")

        op = transactions.Set_withdraw_vesting_route(
            **{"from_account": account,
               "to_account": to,
               "percent": int(percentage * STEEMIT_1_PERCENT),
               "auto_vest": auto_vest
               }
        )

        return self.finalizeOp(op, account, "active")

    def _test_weights_treshold(self, authority):
        weights = 0
        for a in authority["account_auths"]:
            weights += a[1]
        for a in authority["key_auths"]:
            weights += a[1]
        if authority["weight_threshold"] > weights:
            raise ValueError("Threshold too restrictive!")

    def allow(self, foreign, weight=None, permission="posting",
              account=None, threshold=None):
        """ Give additional access to an account by some other public
            key or account.

            :param str foreign: The foreign account that will obtain access
            :param int weight: (optional) The weight to use. If not
                define, the threshold will be used. If the weight is
                smaller than the threshold, additional signatures will
                be required. (defaults to threshold)
            :param str permission: (optional) The actual permission to
                modify (defaults to ``posting``)
            :param str account: (optional) the account to allow access
                to (defaults to ``default_author``)
            :param int threshold: The threshold that needs to be reached
                by signatures to be able to interact
        """
        if not account:
            if "default_author" in config:
                account = config["default_author"]
        if not account:
            raise ValueError("You need to provide an account")

        if permission not in ["owner", "posting", "active"]:
            raise ValueError(
                "Permission needs to be either 'owner', 'posting', or 'active"
            )
        account = self.rpc.get_account(account)
        if not account:
            raise AccountDoesNotExistsException(account)

        if not weight:
            weight = account[permission]["weight_threshold"]

        authority = account[permission]
        try:
            pubkey = PublicKey(foreign)
            authority["key_auths"].append([
                str(pubkey),
                weight
            ])
        except:
            try:
                foreign_account = self.rpc.get_account(foreign)
                authority["account_auths"].append([
                    foreign_account["name"],
                    weight
                ])
            except:
                raise ValueError(
                    "Unknown foreign account or unvalid public key"
                )
        if threshold:
            authority["weight_threshold"] = threshold
            self._test_weights_treshold(authority)

        op = transactions.Account_update(
            **{"account": account["name"],
                permission: authority,
                "memo_key": account["memo_key"],
                "json_metadata": account["json_metadata"]}
        )
        if permission == "owner":
            return self.finalizeOp(op, account["name"], "owner")
        else:
            return self.finalizeOp(op, account["name"], "active")

    def disallow(self, foreign, permission="posting",
                 account=None, threshold=None):
        """ Remove additional access to an account by some other public
            key or account.

            :param str foreign: The foreign account that will obtain access
            :param str permission: (optional) The actual permission to
                modify (defaults to ``posting``)
            :param str account: (optional) the account to allow access
                to (defaults to ``default_author``)
            :param int threshold: The threshold that needs to be reached
                by signatures to be able to interact
        """
        if not account:
            if "default_author" in config:
                account = config["default_author"]
        if not account:
            raise ValueError("You need to provide an account")

        if permission not in ["owner", "posting", "active"]:
            raise ValueError(
                "Permission needs to be either 'owner', 'posting', or 'active"
            )
        account = self.rpc.get_account(account)
        if not account:
            raise AccountDoesNotExistsException(account)
        authority = account[permission]

        try:
            pubkey = PublicKey(foreign)
            affected_items = list(
                filter(lambda x: x[0] == str(pubkey),
                       authority["key_auths"]))
            authority["key_auths"] = list(filter(
                lambda x: x[0] != str(pubkey),
                authority["key_auths"]
            ))
        except:
            try:
                foreign_account = self.rpc.get_account(foreign)
                affected_items = list(
                    filter(lambda x: x[0] == foreign_account["name"],
                           authority["account_auths"]))
                authority["account_auths"] = list(filter(
                    lambda x: x[0] != foreign_account["name"],
                    authority["account_auths"]
                ))
            except:
                raise ValueError(
                    "Unknown foreign account or unvalid public key"
                )

        removed_weight = affected_items[0][1]

        # Define threshold
        if threshold:
            authority["weight_threshold"] = threshold

        # Correct threshold (at most by the amount removed from the
        # authority)
        try:
            self._test_weights_treshold(authority)
        except:
            log.critical(
                "The account's threshold will be reduced by %d"
                % (removed_weight)
            )
            authority["weight_threshold"] -= removed_weight
            self._test_weights_treshold(authority)

        op = transactions.Account_update(
            **{"account": account["name"],
                permission: authority,
                "memo_key": account["memo_key"],
                "json_metadata": account["json_metadata"]}
        )
        if permission == "owner":
            return self.finalizeOp(op, account["name"], "owner")
        else:
            return self.finalizeOp(op, account["name"], "active")

    def update_memo_key(self, key, account=None):
        """ Update an account's memo public key

            This method does **not** add any private keys to your
            wallet but merely changes the memo public key.

            :param str key: New memo public key
            :param str account: (optional) the account to allow access
                to (defaults to ``default_author``)
        """
        if not account:
            if "default_author" in config:
                account = config["default_author"]
        if not account:
            raise ValueError("You need to provide an account")

        PublicKey(key)  # raises exception if invalid

        account = self.rpc.get_account(account)
        if not account:
            raise AccountDoesNotExistsException(account)

        op = transactions.Account_update(
            **{"account": account["name"],
                "memo_key": key,
                "json_metadata": account["json_metadata"]}
        )
        return self.finalizeOp(op, account["name"], "active")

    def approve_witness(self, witness, account=None, approve=True):
        """ Vote **for** a witness. This method adds a witness to your
            set of approved witnesses. To remove witnesses see
            ``disapprove_witness``.

            :param str witness: witness to approve
            :param str account: (optional) the account to allow access
                to (defaults to ``default_author``)
        """
        if not account:
            if "default_author" in config:
                account = config["default_author"]
        if not account:
            raise ValueError("You need to provide an account")

        account = self.rpc.get_account(account)
        if not account:
            raise AccountDoesNotExistsException(account)

        op = transactions.Account_witness_vote(
            **{"account": account["name"],
               "witness": witness,
               "approve": approve,
               })
        return self.finalizeOp(op, account["name"], "active")

    def disapprove_witness(self, witness, account=None, approve=True):
        """ Remove vote for a witness. This method removes
            a witness from your set of approved witnesses. To add
            witnesses see ``approve_witness``.

            :param str witness: witness to approve
            :param str account: (optional) the account to allow access
                to (defaults to ``default_author``)
        """
        return self.approve_witness(self, witness=witness, account=account, approve=False)

    def custom_json(self, id, json, required_auths=[], required_posting_auths=[]):
        """ Create a custom json operation

            :param str id: identifier for the custom json (max length 32 bytes)
            :param json json: the json data to put into the custom_json operation
            :param list required_auths: (optional) required auths
            :param list required_posting_auths: (optional) posting auths
        """
        account = None
        if len(required_auths):
            account = required_auths[0]
        elif len(required_posting_auths):
            account = required_posting_auths[0]
        else:
            raise Exception("At least on account needs to be specified")
        op = transactions.Custom_json(
            **{"json": json,
               "required_auths": required_auths,
               "required_posting_auths": required_posting_auths,
               "id": id})
        return self.finalizeOp(op, account, "posting")

    def resteem(self, identifier, account=None):
        """ Resteem a post

            :param str identifier: post identifier (@<account>/<permlink>)
            :param str account: (optional) the account to allow access
                to (defaults to ``default_author``)
        """
        if not account:
            if "default_author" in config:
                account = config["default_author"]
        if not account:
            raise ValueError("You need to provide an account")
        author, permlink = resolveIdentifier(identifier)
        return self.custom_json(
            id="follow",
            json=["reblog",
                  {"account": account,
                   "author": author,
                   "permlink": permlink
                   }],
            required_posting_auths=[account]
        )

    def unfollow(self, unfollow, what=["blog"], account=None):
        """ Unfollow another account's blog

            :param str unfollow: Follow this account
            :param list what: List of states to follow (defaults to ``['blog']``)
            :param str account: (optional) the account to allow access
                to (defaults to ``default_account``)
        """
        # FIXME: removing 'blog' from the array requires to first read
        # the follow.what from the blockchain
        return self.follow(unfollow, what=[], account=account)

    def follow(self, follow, what=["blog"], account=None):
        """ Follow another account's blog

            :param str follow: Follow this account
            :param list what: List of states to follow (defaults to ``['blog']``)
            :param str account: (optional) the account to allow access
                to (defaults to ``default_account``)
        """
        if not account:
            if "default_account" in config:
                account = config["default_account"]
        if not account:
            raise ValueError("You need to provide an account")
        return self.custom_json(
            id="follow",
            json=['follow', {
                'follower': account,
                'following': follow,
                'what': what}],
            required_posting_auths=[account]
        )

    def reblog(self, *args, **kwargs):
        """ See resteem() """
        self.resteem(*args, **kwargs)

    def update_account_profile(self, profile, account=None):
        """ Update an account's meta data (json_meta)

            :param dict json: The meta data to use (use Profile() from profile.py)
            :param str account: (optional) the account to allow access
                to (defaults to ``default_account``)
        """
        assert isinstance(profile, Profile)
        if not account:
            if "default_author" in config:
                account = config["default_account"]
        if not account:
            raise ValueError("You need to provide an account")

        account = self.rpc.get_account(account)
        if not account:
            raise AccountDoesNotExistsException(account)

        op = transactions.Account_update(
            **{"account": account["name"],
                "memo_key": account["memo_key"],
                "json_metadata": str(profile)}
        )
        return self.finalizeOp(op, account["name"], "active")

    #######################################################
    # Exchange stuff
    #######################################################

    def dex(self, account=None, loadactivekey=False):
        ex_config = PistonExchangeConfig
        if not account:
            if "default_account" in config:
                ex_config.account = config["default_account"]
        else:
            ex_config.account = account
        if loadactivekey and not self.unsigned:
            if not ex_config.account:
                raise ValueError("You need to provide an account")
            ex_config.wif = self.wallet.getActiveKeyForAccount(
                ex_config.account
            )
        return SteemExchange(
            ex_config,
            safe_mode=self.nobroadcast or self.unsigned,
        )

    def returnOrderBook(self, *args):
        return self.dex().returnOrderBook(*args)

    def returnTicker(self):
        return self.dex().returnTicker()

    def return24Volume(self):
        return self.dex().return24Volume()

    def returnTradeHistory(self, *args):
        return self.dex().returnTradeHistory(*args)

    def returnMarketHistoryBuckets(self):
        return self.dex().returnMarketHistoryBuckets()

    def returnMarketHistory(self, *args):
        return self.dex().returnMarketHistory(*args)

    def buy(self, *args, account=None):
        tx = self.dex(account=account, loadactivekey=True).buy(*args)
        if self.unsigned:
            return self._addUnsignedTxParameters(tx, account, "active")
        else:
            return tx

    def sell(self, *args, account=None):
        tx = self.dex(account=account, loadactivekey=True).sell(*args)
        if self.unsigned:
            return self._addUnsignedTxParameters(tx, account, "active")
        else:
            return tx


class SteemConnector(object):

    #: The static steem connection
    steem = None

    def __init__(self, *args, **kwargs):
        """ This class is a singelton and makes sure that only one
            connection to the Steem node is established and shared among
            flask threads.
        """
        if not SteemConnector.steem:
            self.connect(*args, **kwargs)

    def getSteem(self):
        return SteemConnector.steem

    def connect(self, *args, **kwargs):
        log.debug("trying to connect to %s" % config["node"])
        try:
            SteemConnector.steem = Steem(*args, **kwargs)
        except NoAccessApi as e:
            print("=" * 80)
            print(str(e))
            print("=" * 80)
            exit(1)
        except Exception as e:
            print(
                "No connection to %s could be established!\n" % config["node"] +
                "Please try again later, or select another node via:\n"
                "    piston node wss://example.com\n\n"
                "Error: \n" + str(e)
            )
            print("=" * 80)
            exit(1)


class PistonExchangeConfig():
    witness_url           = config["node"]
    witness_user          = config["rpcuser"]
    witness_password      = config["rpcpassword"]
    account               = config["default_account"]
    wif                   = None
