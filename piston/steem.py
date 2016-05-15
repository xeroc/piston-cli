from steemapi.steemclient import SteemNodeRPC
from steembase import PrivateKey, PublicKey, Address
import steembase.transactions as transactions
from piston.utils import (
    resolveIdentifier,
)
from piston.wallet import Wallet
from piston.configuration import Configuration
config = Configuration()

if "node" not in config or not config["node"]:
    config["node"] = "wss://steemit.com/ws"

rpc = None
nobroad = False


def executeOp(op, wif=None):
    if not wif:
        print("Missing required key")
        return

    ops    = [transactions.Operation(op)]
    expiration = transactions.formatTimeFromNow(30)
    ref_block_num, ref_block_prefix = transactions.getBlockParams(rpc)
    tx     = transactions.Signed_Transaction(
        ref_block_num=ref_block_num,
        ref_block_prefix=ref_block_prefix,
        expiration=expiration,
        operations=ops
    )
    tx = tx.sign([wif])

    if not nobroad:
        if isinstance(tx, transactions.Signed_Transaction):
            tx = transactions.JsonObj(tx)
        reply = rpc.broadcast_transaction(tx, api="network_broadcast")
        if reply:
            print(reply)
    else:
        print("Not broadcasting anything!")
        reply = None

    return tx


def connect(node=None, rpcuser=None, rpcpassword=None, nobroadcast=False):
    global nobroad
    global rpc
    nobroad = nobroadcast
    if not node:
        if "node" in config:
            node = config["node"]
        else:
            raise ValueError("A Steem node needs to be provided!")

    if not rpcuser and "rpcuser" in config:
        rpcuser = config["rpcuser"]

    if not rpcpassword and "rpcpassword" in config:
        rpcpassword = config["rpcpassword"]

    rpc = SteemNodeRPC(node, rpcuser, rpcpassword)
    return rpc


def reply(reply_identifier="", author="", permlink="", title="", body="", meta=None):
    post(author, permlink, title, body, meta, reply_identifier)


def edit(identifier="", body="", meta=None, replace=False):
    post_author, post_permlink = resolveIdentifier(identifier)
    original_post = rpc.get_content(post_author, post_permlink)

    if replace:
        newbody = body
    else:
        import diff_match_patch
        dmp = diff_match_patch.diff_match_patch()
        patch = dmp.patch_make(original_post["body"], body)
        newbody = dmp.patch_toText(patch)

        if not newbody:
            print("No changes made! Skipping ...")
            return

    post(**{"parent_author": original_post["parent_author"],
            "parent_permlink": original_post["parent_permlink"],
            "author": original_post["author"],
            "permlink": original_post["permlink"],
            "title": original_post["title"],
            "body": newbody,
            "meta": original_post["json_metadata"]})


def post(author="", permlink="",
         title="", body="", meta="",
         reply_identifier=None, category=""):

    if reply_identifier and not category:
        parent_author, parent_permlink = resolveIdentifier(reply_identifier)
    elif category and not reply_identifier:
        parent_permlink = category
        parent_author = ""
    elif not category and not reply_identifier:
        parent_author = ""
        parent_permlink = ""
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
    wif = Wallet(rpc).getPostingKeyForAccount(author)
    executeOp(op, wif)


def vote(identifier, weight, voter=None):

    STEEMIT_100_PERCENT = 10000
    STEEMIT_1_PERCENT = (STEEMIT_100_PERCENT / 100)

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
    wif = Wallet(rpc).getPostingKeyForAccount(voter)
    executeOp(op, wif)


def get_content(identifier):
    post_author, post_permlink = resolveIdentifier(identifier)
    return rpc.get_content(post_author, post_permlink)


def get_replies(author, skipown=True):
    state = rpc.get_state("/@%s/recent-replies" % author)
    replies = state["accounts"][author]["recent_replies"]
    discussions  = []
    for reply in replies:
        post = state["content"][reply]
        if skipown and post["author"] != author:
            discussions.append(post)
    return discussions


def get_posts(limit=10,
              sort="recent",
              category=None,
              start=None,):
    from functools import partial
    if sort == "recent":
        if category:
            func = partial(rpc.get_discussions_in_category_by_last_update, category)
        else:
            func = rpc.get_discussions_by_last_update
    elif sort == "payout":
        if category:
            func = partial(rpc.get_discussions_in_category_by_total_pending_payout, category)
        else:
            func = rpc.get_discussions_by_total_pending_payout
    else:
        print("Invalid choice of '--sort'!")
        return

    author = ""
    permlink = ""
    if start:
        author, permlink = resolveIdentifier(start)

    return func(author, permlink, limit)
