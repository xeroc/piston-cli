import re
import json
import string
import random
from steemapi.steemclient import SteemNodeRPC
from steembase.account import PrivateKey, PublicKey, Address
import steembase.transactions as transactions
from .utils import (
    resolveIdentifier,
    constructIdentifier,
    derivePermlink,
    formatTimeString
)
from .wallet import Wallet
from .storage import configStorage as config
from datetime import datetime, timedelta
import logging
log = logging.getLogger(__name__)

prefix = "STM"
# prefix = "TST"

STEEMIT_100_PERCENT = 10000
STEEMIT_1_PERCENT = (STEEMIT_100_PERCENT / 100)


class AccountExistsException(Exception):
    pass


class Post(object):
    """ This object gets instanciated by Steem.streams and is used as an
        abstraction layer for Comments in Steem

        :param Steem steem: An instance of the Steem() object
        :param object post: The post as obtained by `get_content`
    """
    steem = None

    def __init__(self, steem, post):
        if not isinstance(steem, Steem):
            raise ValueError(
                "First argument must be instance of Steem()"
            )
        self.steem = steem
        self._patch = False

        # Get full Post
        if isinstance(post, str):  # From identifier
            self.identifier = post
            post_author, post_permlink = resolveIdentifier(post)
            post = self.steem.rpc.get_content(post_author, post_permlink)

        elif (isinstance(post, dict) and  # From dictionary
                "author" in post and
                "permlink" in post):
            # strip leading @
            if post["author"][0] == "@":
                post["author"] = post["author"][1:]
            self.identifier = constructIdentifier(
                post["author"],
                post["permlink"]
            )
            # if there only is an author and a permlink but no body
            # get the full post via RPC
            if "created" not in post or "cashout_time" not in post:
                post = self.steem.rpc.get_content(
                    post["author"],
                    post["permlink"]
                )
        else:
            raise ValueError("Post expects an identifier or a dict "
                             "with author and permlink!")

        # If this 'post' comes from an operation, it might carry a patch
        if "body" in post and re.match("^@@", post["body"]):
            self._patched = True
            self._patch = post["body"]

        # Parse Times
        parse_times = ["active",
                       "cashout_time",
                       "created",
                       "last_payout",
                       "last_update",
                       "max_cashout_time"]
        for p in parse_times:
            post["%s_parsed" % p] = datetime.strptime(
                post.get(p, "1970-01-01T00:00:00"), '%Y-%m-%dT%H:%M:%S'
            )

        # Try to properly format json meta data
        meta_str = post.get("json_metadata", "")
        post["_json_metadata"] = meta_str
        meta = {}
        try:
            meta = json.loads(meta_str)
        except:
            pass
        post["_tags"] = meta.get("tags", [])

        # Retrieve the root comment
        self.openingPostIdentifier, self.category = self._getOpeningPost()

        # Total reward
        post["total_payout_reward"] = "%.3f SBD" % (
            float(post["total_payout_value"].split(" ")[0]) +
            float(post["total_pending_payout_value"].split(" ")[0])
        )

        # Store everything as attribute
        for key in post:
            setattr(self, key, post[key])

    def _getOpeningPost(self):
        m = re.match("/([^/]*)/@([^/]*)/([^#]*).*",
                     getattr(self, "url", ""))
        if not m:
            return None, None
        else:
            category = m.group(1)
            author = m.group(2)
            permlink = m.group(3)
            return constructIdentifier(
                author, permlink
            ), category

    def __getitem__(self, key):
        return getattr(self, key)

    def remove(self, key):
        delattr(self, key)

    def get(self, key, default=None):
        if hasattr(self, key):
            return getattr(self, key)
        else:
            return default

    def __delitem__(self, key):
        delattr(self, key)

    def __contains__(self, key):
        return hasattr(self, key)

    def __iter__(self):
        r = {}
        for key in vars(self):
            r[key] = getattr(self, key)
        return iter(r)

    def __len__(self):
        return len(vars(self))

    def __repr__(self):
        return "<Steem.Post-%s>" % constructIdentifier(self["author"], self["permlink"])

    def get_comments(self, sort="total_payout_reward"):
        """ Return **first-level** comments of the post.
        """
        post_author, post_permlink = resolveIdentifier(self.identifier)
        posts = self.steem.rpc.get_content_replies(post_author, post_permlink)
        r = []
        for post in posts:
            r.append(Post(self.steem, post))
        if sort == "total_payout_value":
            r = sorted(r, key=lambda x: float(
                x["total_payout_value"].split(" ")[0]
            ), reverse=True)
        elif sort == "total_payout_reward":
            r = sorted(r, key=lambda x: float(
                x["total_payout_reward"].split(" ")[0]
            ), reverse=True)
        else:
            r = sorted(r, key=lambda x: x[sort])
        return(r)

    def reply(self, body, title="", author="", meta=None):
        """ Reply to the post

            :param str body: (required) body of the reply
            :param str title: Title of the reply
            :param str author: Author of reply
            :param json meta: JSON Meta data
        """
        return self.steem.reply(self.identifier, body, title, author, meta)

    def upvote(self, weight=+100, voter=None):
        """ Upvote the post

            :param float weight: (optional) Weight for posting (-100.0 - +100.0) defaults to +100.0
            :param str voter: (optional) Voting account
        """
        return self.vote(weight, voter=voter)

    def downvote(self, weight=-100, voter=None):
        """ Downvote the post

            :param float weight: (optional) Weight for posting (-100.0 - +100.0) defaults to -100.0
            :param str voter: (optional) Voting account
        """
        return self.vote(weight, voter=voter)

    def vote(self, weight, voter=None):
        """ Vote the post

            :param float weight: Weight for posting (-100.0 - +100.0)
            :param str voter: Voting account
        """
        return self.steem.vote(self.identifier, weight, voter=voter)


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

    def __init__(self, *args, **kwargs):
        """
            :param bool debug: Enable Debugging
            :param wif wif: WIF private key for signing. If provided,
                            will not load from wallet (optional). Can be
                            single string, or array of keys.
        """
        self.connect(*args, **kwargs)
        self.debug = kwargs.get("debug", False)
        self.nobroadcast = kwargs.get("nobroadcast", False)

        if "wif" in kwargs:
            self.wallet = Wallet(self.rpc, wif=kwargs["wif"])
        else:
            self.wallet = Wallet(self.rpc)

    def connect(self, *args, **kwargs):
        """ Connect to the Steem network.

            :param str node: Node to connect to *(optional)*
            :param str rpcuser: RPC user *(optional)*
            :param str rpcpassword: RPC password *(optional)*
            :param bool nobroadcast: Do **not** broadcast a transaction!

            If no node is provided, it will connect to the node of
            http://piston.rocks. It is **highly** recommended that you pick your own
            node instead. Default settings can be changed with:

            .. code-block:: python

                piston set node <host>

            where ``<host>`` starts with ``ws://`` or ``wss://``.
        """

        node = None
        rpcuser = None
        rpcpassword = None
        if len(args):
            node = args.pop(0)
        if len(args):
            rpcuser = args.pop(0)
        if len(args):
            rpcpassword = args.pop(0)
        node = kwargs.pop("node", node)
        rpcuser = kwargs.pop("rpcuser", rpcuser)
        rpcpassword = kwargs.pop("rpcpassword", rpcpassword)

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

    def executeOp(self, op, wif=None):
        """ Execute an operation by signing it with the ``wif`` key and
            broadcasting it to the Steem network

            :param Object op: The operation to be signed and broadcasts as
                              provided by the ``transactions`` class.
            :param string wif: The wif key to use for signing a transaction

            **TODO**: The full node could, given the operations, give us a
            set of public keys that are required for signing, then the
            public keys could used to identify the wif-keys from the wallet.

        """
        # overwrite wif with default wif if available
        if not wif:
            raise MissingKeyError

        ops = [transactions.Operation(op)]
        expiration = transactions.formatTimeFromNow(30)
        ref_block_num, ref_block_prefix = transactions.getBlockParams(self.rpc)
        tx = transactions.Signed_Transaction(
            ref_block_num=ref_block_num,
            ref_block_prefix=ref_block_prefix,
            expiration=expiration,
            operations=ops
        )
        tx = tx.sign([wif])
        tx = transactions.JsonObj(tx)

        if self.debug:
            log.debug(str(tx))

        if not self.nobroadcast:
            try:
                self.rpc.broadcast_transaction(tx, api="network_broadcast")
            except:
                raise BroadcastingError
        else:
            log.warning("Not broadcasting anything!")

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
             category=""):
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
            :param str category: Allows to define a category for new posts.
                                 It is highly recommended to provide a
                                 category as posts end up in ``spam``
                                 otherwise.
        """

        if not author and config["default_author"]:
            author = config["default_author"]

        if not author:
            raise ValueError(
                "Please define an author. (Try 'piston set default_author'"
            )

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
        wif = self.wallet.getPostingKeyForAccount(author)
        return self.executeOp(op, wif)

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
        wif = self.wallet.getPostingKeyForAccount(voter)
        return self.executeOp(op, wif)

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

        owner   = format(posting_pubkey, prefix)
        active  = format(active_pubkey, prefix)
        posting = format(owner_pubkey, prefix)
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
        wif = self.wallet.getActiveKeyForAccount(creator)
        return self.executeOp(op, wif)

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
        wif = self.wallet.getActiveKeyForAccount(account)
        return self.executeOp(op, wif)

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
        wif = self.wallet.getActiveKeyForAccount(account)
        return self.executeOp(op, wif)

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
            if "default_account" in config:
                to = config["default_account"]
        if not to:
            raise ValueError("You need to provide a 'to' account")

        op = transactions.Transfer_to_vesting(
            **{"from": account,
               "to": to,
               "amount": '{:.{prec}f} {asset}'.format(
                   float(amount),
                   prec=3,
                   asset="STEEM"
               ),
               }
        )
        wif = self.wallet.getActiveKeyForAccount(account)
        return self.executeOp(op, wif)

    def get_content(self, identifier):
        """ Get the full content of a post.

            :param str identifier: Identifier for the post to upvote Takes
                                   the form ``@author/permlink``
        """
        post_author, post_permlink = resolveIdentifier(identifier)
        return Post(self, self.rpc.get_content(post_author, post_permlink))

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
            post = state["content"]["%s/%s" % (
                user, p   # FIXME, this is a inconsistency in steem backend
            )]
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
        info = self.rpc.get_dynamic_global_properties()
        steem_per_mvest = (
            float(info["total_vesting_fund_steem"].split(" ")[0]) /
            (float(info["total_vesting_shares"].split(" ")[0]) / 1e6)
        )
        vesting_shares_steem = float(a["vesting_shares"].split(" ")[0]) / 1e6 * steem_per_mvest
        return {
            "balance": a["balance"],
            "vesting_shares" : a["vesting_shares"],
            "vesting_shares_steem" : vesting_shares_steem,
            "sbd_balance": a["sbd_balance"]
        }

    def get_account_history(self, account, end=100, limit=100, only_ops=[]):
        """ Returns the transaction history of an account

            :param str account: account name to get history for
            :param int end: sequence number of the last transaction to return
            :param int limit: limit number of transactions to return
            :param array only_ops: Limit generator by these operations
        """
        r = []
        for op in self.loop_account_history(account, end, limit, only_ops):
            r.append(op)
        return r

    def loop_account_history(self, account, end=100, limit=100, only_ops=[]):
        """ Returns a generator for individual account transactions

            :param str account: account name to get history for
            :param int end: sequence number of the last transaction to return
            :param int limit: limit number of transactions to return
            :param array only_ops: Limit generator by these operations
        """
        cnt = 0
        if end < limit:
            limit = end
        if limit > 100:
            _limit = 100
        else:
            _limit = limit
        while (cnt < limit) and end >= limit:

            txs = self.rpc.get_account_history(account, end, _limit)
            for i in txs:
                if not only_ops or i[1]["op"][0] in only_ops:
                    cnt += 1
                    yield i
                if cnt > limit:
                    break
            end = txs[0][0] - 1  # new end

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
            :param floag percentage: The percent of the withdraw to go
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
        wif = self.wallet.getActiveKeyForAccount(account)
        return self.executeOp(op, wif)
