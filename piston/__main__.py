#!/usr/bin/env python3

import sys
import os
import argparse
from steemapi.steemclient import SteemNodeRPC
from pprint import pprint
from steembase import PrivateKey, PublicKey, Address
import steembase.transactions as transactions
from piston.wallet import Wallet
import frontmatter

from prettytable import PrettyTable


def broadcastTx(tx):
    if isinstance(tx, transactions.Signed_Transaction):
        tx     = transactions.JsonObj(tx)
    return rpc.broadcast_transaction(tx, api="network_broadcast")


def resolveIdentifier(identifier):
        import re
        match = re.match("@?(\w*)/([\w-]*)", identifier)
        return match.group(1), match.group(2)


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

    pprint(transactions.JsonObj(tx))

    if not args.nobroadcast:
        reply = broadcastTx(tx)
        if reply:
            print(reply)
    else:
        print("Not broadcasting anything!")
        reply = None


def main() :
    global args

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Command line tool to interact with the STEEM network"
    )

    """
        Default settings for all tools
    """
    parser.add_argument(
        '--node',
        type=str,
        default='wss://steemit.com/ws',
        help='Websocket URL for public Steem API (default: "wss://steemit.com/ws")'
    )
    parser.add_argument(
        '--rpcuser',
        type=str,
        default='',
        help='Websocket user if authentication is required'
    )
    parser.add_argument(
        '--rpcpassword',
        type=str,
        default='',
        help='Websocket password if authentication is required'
    )
    parser.add_argument(
        '--nobroadcast',
        action='store_true',
        help='Do not broadcast anything'
    )
    subparsers = parser.add_subparsers(help='sub-command help')
    parser.set_defaults(command=None)

    """
        Command "addkey"
    """
    addkey = subparsers.add_parser('addkey', help='Add a new key to the wallet')
    addkey.add_argument(
        'wifkey',
        type=str,
        help='the private key in wallet import format (wif)'
    )
    addkey.set_defaults(command="addkey")

    """
        Command "listkeys"
    """
    listkeys = subparsers.add_parser('listkeys', help='List available keys in your wallet')
    listkeys.set_defaults(command="listkeys")

    """
        Command "listaccounts"
    """
    listaccounts = subparsers.add_parser('listaccounts', help='List available accounts in your wallet')
    listaccounts.set_defaults(command="listaccounts")

    """
        Command "list"
    """
    parser_list = subparsers.add_parser('list', help='List posts on STEAM')
    parser_list.set_defaults(command="list")
    parser_list.add_argument(
        '--author',
        type=str,
        help='Only posts by this author'
    )
    parser_list.add_argument(
        '--category',
        type=str,
        help='Only posts with in this category'
    )
    parser_list.add_argument(
        '--sort',
        type=str,
        default="recent",
        choices=["recent", "payout"],
        help='Sort posts'
    )
    parser_list.add_argument(
        '--limit',
        type=int,
        default=10,
        help='Limit posts by number'
    )

    """
        Command "categories"
    """
    parser_categories = subparsers.add_parser('categories', help='Show categories')
    parser_categories.set_defaults(command="categories")
    parser_categories.add_argument(
        '--sort',
        type=str,
        default="trending",
        choices=["trending", "best", "active", "recent"],
        help='Sort categories'
    )
    parser_categories.add_argument(
        'category',
        nargs="?",
        type=str,
        help='Only categories used by this author'
    )
    parser_categories.add_argument(
        '--limit',
        type=int,
        default=10,
        help='Limit categories by number'
    )

    """
        Command "read"
    """
    parser_read = subparsers.add_parser('read', help='Read a post on Steem')
    parser_read.set_defaults(command="read")
    parser_read.add_argument(
        'post',
        type=str,
        help='@author/permlink-identifier of the post to read (e.g. @xeroc/python-steem-0-1)'
    )
    parser_read.add_argument(
        '--yaml',
        action='store_true',
        help='Show YAML formated header'
    )
    parser_read.add_argument(
        '--comments',
        action='store_true',
        help='Also show all comments'
    )

    """
        Command "post"
    """
    parser_post = subparsers.add_parser('post', help='Post something new')
    parser_post.set_defaults(command="post")
    parser_post.add_argument(
        '--author',
        type=str,
        required=True,
        help='Publish post as this user (requires to have the key installed in the wallet)'
    )
    parser_post.add_argument(
        '--permlink',
        type=str,
        required=True,
        help='The permlink (together with the author identifies the post uniquely)'
    )
    parser_post.add_argument(
        '--category',
        default="",
        type=str,
        help='Specify category'
    )
    parser_post.add_argument(
        '--title',
        type=str,
        required=True,
        help='Title of the post'
    )

    """
        Command "yaml"
    """
    parser_yaml = subparsers.add_parser('yaml', help='yaml something new')
    parser_yaml.set_defaults(command="yaml")
    parser_yaml.add_argument(
        'file',
        nargs='?',
        type=str,
        default=None,
        help='Filename to open. If not present, or "-", stdin will be used'
    )
    parser_yaml.add_argument(
        '--author',
        type=str,
        help='Publish post as this user (requires to have the key installed in the wallet)'
    )
    parser_yaml.add_argument(
        '--permlink',
        type=str,
        help='The permlink (together with the author identifies the post uniquely)'
    )
    parser_yaml.add_argument(
        '--title',
        type=str,
        help='Title of the post'
    )

    """
        Command "reply"
    """
    reply = subparsers.add_parser('reply', help='Reply to an existing post')
    reply.set_defaults(command="reply")
    reply.add_argument(
        'replyto',
        type=str,
        help='@author/permlink-identifier of the post to reply to (e.g. @xeroc/python-steem-0-1)'
    )
    reply.add_argument(
        '--author',
        type=str,
        required=True,
        help='Publish post as this user (requires to have the key installed in the wallet)'
    )
    reply.add_argument(
        '--permlink',
        type=str,
        required=True,
        help='The permlink (together with the author identifies the post uniquely)'
    )
    reply.add_argument(
        '--title',
        type=str,
        required=True,
        help='Title of the post'
    )

    """
        Command "edit"
    """
    parser_edit = subparsers.add_parser('edit', help='Edit to an existing post')
    parser_edit.set_defaults(command="edit")
    parser_edit.add_argument(
        'post',
        type=str,
        help='@author/permlink-identifier of the post to edit to (e.g. @xeroc/python-steem-0-1)'
    )
    parser_edit.add_argument(
        '--author',
        type=str,
        required=False,
        help='Post an edit as another author'
    )
    parser_edit.add_argument(
        '--file',
        type=str,
        required=False,
        help='Patch with content of this file'
    )
    parser_edit.add_argument(
        '--replace',
        action='store_true',
        help="Don't patch but replace original post (will make you lose votes)"
    )

    """
        Command "upvote"
    """
    parser_upvote = subparsers.add_parser('upvote', help='Upvote a post')
    parser_upvote.set_defaults(command="upvote")
    parser_upvote.add_argument(
        'post',
        type=str,
        help='@author/permlink-identifier of the post to upvote to (e.g. @xeroc/python-steem-0-1)'
    )
    parser_upvote.add_argument(
        '--voter',
        type=str,
        required=True,
        help='The voter account name'
    )
    parser_upvote.add_argument(
        '--weight',
        type=float,
        default=100.0,
        required=False,
        help='Actual weight (from 0.1 to 100.0)'
    )

    """
        Command "downvote"
    """
    parser_downvote = subparsers.add_parser('downvote', help='Downvote a post')
    parser_downvote.set_defaults(command="downvote")
    parser_downvote.add_argument(
        '--voter',
        type=str,
        required=True,
        help='The voter account name'
    )
    parser_downvote.add_argument(
        'post',
        type=str,
        help='@author/permlink-identifier of the post to downvote to (e.g. @xeroc/python-steem-0-1)'
    )
    parser_downvote.add_argument(
        '--weight',
        type=float,
        default=100.0,
        required=False,
        help='Actual weight (from 0.1 to 100.0)'
    )

    """
        Parse Arguments
    """
    args = parser.parse_args()

    global rpc
    rpc = SteemNodeRPC(args.node, args.rpcuser, args.rpcpassword)

    if args.command == "addkey":
        print(Wallet(rpc).addPrivateKey(args.wifkey))

    elif args.command == "listkeys":
        t = PrettyTable(["key"])
        t.align = "l"
        for key in Wallet(rpc).getPublicKeys():
            t.add_row([key])
        print(t)

    elif args.command == "listaccounts":
        t = PrettyTable(["name", "key"])
        t.align = "l"
        for account in Wallet(rpc).getAccounts():
            t.add_row(account)
        print(t)

    elif args.command == "reply":
        parent_author, parent_permlink = resolveIdentifier(args.replyto)

        parent = rpc.get_content(parent_author, parent_permlink)
        if parent["id"] == "0.0.0":
            print("Can't find post %s" % args.replyto)
            return

        op = transactions.Comment(
            **{"parent_author": parent["author"],
               "parent_permlink": parent["permlink"],
               "author": args.author,
               "permlink": args.permlink,
               "title": args.title,
               "body": sys.stdin.read(),
               "json_metadata": ""}
        )
        wif = Wallet(rpc).getPostingKeyForAccount(args.author)
        executeOp(op, wif)

    elif args.command == "post":
        op = transactions.Comment(
            **{"parent_author": "",
               "parent_permlink": args.category,
               "author": args.author,
               "permlink": args.permlink,
               "title": args.title,
               "body": sys.stdin.read(),
               "json_metadata": ""}
        )
        wif = Wallet(rpc).getPostingKeyForAccount(args.author)
        executeOp(op, wif)

    elif args.command == "yaml":
        if args.file and args.file != "-":
            if not os.path.isfile(args.file):
                print("File %s does not exist!" % args.file)
                return
            with open(args.file) as fp:
                data = fp.read()
        else:
            data = sys.stdin.read()

        meta, body = frontmatter.parse(data)

        for key in ["author", "permlink", "title"]:
            if getattr(args, key):
                meta[key] = getattr(args, key)

        for required in ["author", "permlink", "title"]:
            if required not in meta:
                print("Front matter incomplete: '%s' required!" % required)
                return
        if "type" in meta and meta["type"] not in ["post", "reply"]:
            print("Type can only be 'post', or 'reply'!")
            return
            if meta["type"] == "reply":
                for required in ["parent_author", "parent_permlink"]:
                    if required not in meta:
                        print("For reply posts, '%s' is required!" % required)
                        return

        op = transactions.Comment(
            **{"parent_author": meta["parent_author"] if "parent_author" in meta else "",
               "parent_permlink": meta["category"] if "category" in meta else "",
               "author": meta["author"],
               "permlink": meta["permlink"],
               "title": meta["title"],
               "body": body,
               "json_metadata": ""}
        )

        wif = Wallet(rpc).getPostingKeyForAccount(meta["author"])
        executeOp(op, wif)

    elif args.command == "edit":
        post_author, post_permlink = resolveIdentifier(args.post)
        post = rpc.get_content(post_author, post_permlink)

        if post["id"] == "0.0.0":
            print("Can't find post %s" % args.post)
            return

        if args.file and args.file != "-":
            if not os.path.isfile(args.file):
                print("File %s does not exist!" % args.file)
                return
            with open(args.file) as fp:
                edited_message = fp.read()
        else:
            import tempfile
            from subprocess import call
            EDITOR = os.environ.get('EDITOR', 'vim')
            edited_message = None

            with tempfile.NamedTemporaryFile(
                suffix=b".yaml",
                prefix=b"piston-"
            ) as fp:
                fp.write(bytes(post["body"], 'ascii'))
                fp.flush()
                call([EDITOR, fp.name])

                fp.seek(0)
                edited_message = fp.read().decode('ascii')

        if args.replace:
            newbody = edited_message
        else:
            author = args.author if args.author else post["author"]
            import diff_match_patch
            dmp = diff_match_patch.diff_match_patch()
            patch = dmp.patch_make(post["body"], edited_message)
            newbody = dmp.patch_toText(patch)

            op = transactions.Comment(
                **{"parent_author": post["parent_author"],
                   "parent_permlink": post["parent_permlink"],
                   "author": post["author"],
                   "permlink": post["permlink"],
                   "title": post["title"],
                   "body": newbody,
                   "json_metadata": ""}
            )

        wif = Wallet(rpc).getPostingKeyForAccount(author)
        executeOp(op, wif)

    elif args.command == "upvote" or args.command == "downvote":
        STEEMIT_100_PERCENT = 10000
        STEEMIT_1_PERCENT = (STEEMIT_100_PERCENT / 100)
        if args.command == "downvote":
            weight = -float(args.weight)
        else:
            weight = +float(args.weight)

        post_author, post_permlink = resolveIdentifier(args.post)

        op = transactions.Vote(
            **{"voter": args.voter,
               "author": post_author,
               "permlink": post_permlink,
               "weight": int(weight * STEEMIT_1_PERCENT)}
        )
        wif = Wallet(rpc).getPostingKeyForAccount(args.voter)
        executeOp(op, wif)

    elif args.command == "read":
        post_author, post_permlink = resolveIdentifier(args.post)

        if not args.comments:
            post = rpc.get_content(post_author, post_permlink)
            if post["id"] == "0.0.0":
                print("Can't find post %s" % args.post)
                return
            if args.yaml:
                meta = post.copy()
                meta.pop("body", None)
                yaml = frontmatter.Post(post["body"], **meta)
                print(frontmatter.dumps(yaml))
            else:
                print(post["body"])
        else:
            dump_recursive_comments(post_author, post_permlink, 0)

    elif args.command == "categories":

        if args.sort == "trending":
            func = rpc.get_trending_categories
        elif args.sort == "best":
            func = rpc.get_best_categories
        elif args.sort == "active":
            func = rpc.get_active_categories
        elif args.sort == "recent":
            func = rpc.get_recent_categories
        else:
            print("Invalid choice of '--sort'!")
            return

        categories = func(args.category, args.limit)
        t = PrettyTable(["name", "discussions", "payouts"])
        t.align = "l"
        for category in categories:
            t.add_row([
                category["name"],
                category["discussions"],
                category["total_payouts"],
            ])
        print(t)

    elif args.command == "list":
        from functools import partial
        from textwrap import wrap
        if args.sort == "recent":
            if args.category:
                func = partial(rpc.get_discussions_in_category_by_last_update, args.category)
            else:
                func = rpc.get_discussions_by_last_update
        elif args.sort == "payout":
            if args.category:
                func = partial(rpc.get_discussions_in_category_by_total_pending_payout, args.category)
            else:
                func = rpc.get_discussions_by_total_pending_payout
        else:
            print("Invalid choice of '--sort'!")
            return

        discussions = func(args.author, "", args.limit)
        t = PrettyTable([
            "identifier",
            "title",
            "category",
            "replies",
            "votes",
            "payouts",
        ])
        t.align = "l"
        t.align["payouts"] = "r"
        t.align["votes"] = "r"
        t.align["replies"] = "c"
        for d in discussions:
            identifier = "@%s/%s" % (d["author"], d["permlink"])
            t.add_row([
                "\n".join(wrap(identifier, 60)),
                "\n".join(wrap(d["title"], 60)),
                d["category"],
                d["children"],
                d["net_rshares"],
                d["pending_payout_value"],
            ])
        print(t)

    else:
        print("No valid command given")


def dump_recursive_comments(post_author, post_permlink, depth):
    import re
    posts = rpc.get_content_replies(post_author, post_permlink)
    for post in posts:
        meta = {}
        for key in ["author", "permlink"]:
            meta[key] = post[key]
        meta["reply"] = "@{author}/{permlink}".format(**post)
        yaml = frontmatter.Post(post["body"], **meta)
        d = frontmatter.dumps(yaml)
        print(re.sub(
            "^", "  " * depth, d, flags=re.MULTILINE
        ))
        reply = rpc.get_content_replies(post["author"], post["permlink"])
        if len(reply):
            dump_recursive_comments(post["author"], post["permlink"], depth + 1)


rpc = None
args = None
if __name__ == '__main__':
    main()
