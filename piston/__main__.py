#!/usr/bin/env python3

import sys
import argparse
from steemapi.steemclient import SteemNodeRPC
from pprint import pprint
from steembase.account import PrivateKey, PublicKey, Address
import steembase.transactions as transactions
from .wallet import Wallet


def broadcastTx(tx):
    if isinstance(tx, transactions.Signed_Transaction):
        tx     = transactions.JsonObj(tx)
    return rpc.broadcast_transaction(tx, api="network_broadcast")


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
    reply = broadcastTx(tx)
    # reply = None
    if not reply:
        pprint(transactions.JsonObj(tx))
    else:
        print(reply)


def main() :

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

    """
        Command "reply"
    """
    parser_replay = subparsers.add_parser('reply', help='Reply to an existing post')
    parser_replay.set_defaults(command="reply")
    parser_replay.add_argument(
        '--replyto',
        type=str,
        required=True,
        help='@author/permlink-identifier of the post to reply to (e.g. @xeroc/python-steem-0.1)'
    )
    parser_replay.add_argument(
        '--author',
        type=str,
        required=True,
        help='Publish post as this user (requires to have the key installed in the wallet)'
    )
    parser_replay.add_argument(
        '--permlink',
        type=str,
        required=True,
        help='The permlink (together with the author identifies the post uniquely)'
    )
    parser_replay.add_argument(
        '--title',
        type=str,
        required=True,
        help='Title of the post'
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
        [print(a) for a in Wallet(rpc).getPublicKeys()]

    elif args.command == "listaccounts":
        for account in Wallet(rpc).getAccounts():
            print(" ".join(account))

    elif args.command == "reply":
        import re
        match = re.match("@?(\w*)/([\w-]*)", args.replyto)
        parent_author = match.group(1)
        parent_permlink = match.group(2)
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
            import os
            if not os.path.isfile(args.file):
                print("File %s does not exist!" % args.file)
                return
            with open(args.file) as fp:
                data = fp.read()
        else:
            data = sys.stdin.read()

        import frontmatter
        meta, body = frontmatter.parse(data)

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

    else:
        print("No valid command given")


rpc = None
if __name__ == '__main__':
    main()
