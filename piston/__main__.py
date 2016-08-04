#!/usr/bin/env python3

import sys
import os
import argparse
from pprint import pprint
from steembase.account import PrivateKey, PublicKey, Address
import steembase.transactions as transactions
from .storage import configStorage as config
from .utils import (
    resolveIdentifier,
    yaml_parse_file,
    formatTime
)
from .ui import (
    dump_recursive_parents,
    dump_recursive_comments,
    list_posts,
    markdownify,
    format_operation_details
)
from .steem import Steem
import frontmatter
import time
from prettytable import PrettyTable

import logging
log = logging.getLogger("piston")
log.setLevel(logging.WARNING)
log.addHandler(logging.StreamHandler())


availableConfigurationKeys = [
    "default_author",
    "default_voter",
    "default_account",
    "node",
    "rpcuser",
    "rpcpassword",
    "default_vote_weight",
    "list_sorting",
    "categories_sorting",
    "limit",
    "post_category",
    "web:user",
    "web:port",
    "web:debug",
    "web:host",
    "web:nobroadcast",
]


def main() :
    global args

    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Command line tool to interact with the Steem network"
    )

    """
        Default settings for all tools
    """
    parser.add_argument(
        '--node',
        type=str,
        default=config["node"],
        help='Websocket URL for public Steem API (default: "wss://this.piston.rocks/")'
    )
    parser.add_argument(
        '--rpcuser',
        type=str,
        default=config["rpcuser"],
        help='Websocket user if authentication is required'
    )
    parser.add_argument(
        '--rpcpassword',
        type=str,
        default=config["rpcpassword"],
        help='Websocket password if authentication is required'
    )
    parser.add_argument(
        '--nobroadcast',
        action='store_true',
        help='Do not broadcast anything'
    )
    parser.add_argument(
        '--verbose', '-v',
        type=int,
        default=3,
        help='Verbosity'
    )
    subparsers = parser.add_subparsers(help='sub-command help')

    """
        Command "set"
    """
    setconfig = subparsers.add_parser('set', help='Set configuration')
    setconfig.add_argument(
        'key',
        type=str,
        choices=availableConfigurationKeys,
        help='Configuration key'
    )
    setconfig.add_argument(
        'value',
        type=str,
        help='Configuration value'
    )
    setconfig.set_defaults(command="set")

    """
        Command "config"
    """
    configconfig = subparsers.add_parser('config', help='show local configuration')
    configconfig.set_defaults(command="config")

    """
        Command "changewalletpassphrase"
    """
    changepasswordconfig = subparsers.add_parser('changewalletpassphrase', help='Change wallet password')
    changepasswordconfig.set_defaults(command="changewalletpassphrase")

    """
        Command "addkey"
    """
    addkey = subparsers.add_parser('addkey', help='Add a new key to the wallet')
    addkey.add_argument(
        'wifkeys',
        nargs='*',
        type=str,
        help='the private key in wallet import format (wif)'
    )
    addkey.set_defaults(command="addkey")

    """
        Command "delkey"
    """
    delkey = subparsers.add_parser('delkey', help='Delete keys from the wallet')
    delkey.add_argument(
        'pub',
        nargs='*',
        type=str,
        help='the public key to delete from the wallet'
    )
    delkey.set_defaults(command="delkey")

    """
        Command "getkey"
    """
    getkey = subparsers.add_parser('getkey', help='Dump the privatekey of a pubkey from the wallet')
    getkey.add_argument(
        'pub',
        type=str,
        help='the public key for which to show the private key'
    )
    getkey.set_defaults(command="getkey")

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
    parser_list = subparsers.add_parser('list', help='List posts on Steem')
    parser_list.set_defaults(command="list")
    parser_list.add_argument(
        '--start',
        type=str,
        help='Start list from this identifier (pagination)'
    )
    parser_list.add_argument(
        '--category',
        type=str,
        help='Only posts with in this category'
    )
    parser_list.add_argument(
        '--sort',
        type=str,
        default=config["list_sorting"],
        choices=["trending", "created", "active", "cashout", "payout", "votes", "children", "hot"],
        help='Sort posts'
    )
    parser_list.add_argument(
        '--limit',
        type=int,
        default=config["limit"],
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
        default=config["categories_sorting"],
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
        default=config["limit"],
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
        '--full',
        action='store_true',
        help='Show full header information (YAML formated)'
    )
    parser_read.add_argument(
        '--comments',
        action='store_true',
        help='Also show all comments'
    )
    parser_read.add_argument(
        '--parents',
        type=int,
        default=0,
        help='Show x parents for the reply'
    )
    parser_read.add_argument(
        '--format',
        type=str,
        default=config["format"],
        help='Format post',
        choices=["markdown", "raw"],
    )

    """
        Command "post"
    """
    parser_post = subparsers.add_parser('post', help='Post something new')
    parser_post.set_defaults(command="post")
    parser_post.add_argument(
        '--author',
        type=str,
        required=False,
        default=config["default_author"],
        help='Publish post as this user (requires to have the key installed in the wallet)'
    )
    parser_post.add_argument(
        '--permlink',
        type=str,
        required=False,
        help='The permlink (together with the author identifies the post uniquely)'
    )
    parser_post.add_argument(
        '--category',
        default=config["post_category"],
        type=str,
        help='Specify category'
    )
    parser_post.add_argument(
        '--title',
        type=str,
        required=False,
        help='Title of the post'
    )
    parser_post.add_argument(
        '--file',
        type=str,
        default=None,
        help='Filename to open. If not present, or "-", stdin will be used'
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
        required=False,
        default=config["default_author"],
        help='Publish post as this user (requires to have the key installed in the wallet)'
    )
    reply.add_argument(
        '--permlink',
        type=str,
        required=False,
        help='The permlink (together with the author identifies the post uniquely)'
    )
    reply.add_argument(
        '--title',
        type=str,
        required=False,
        help='Title of the post'
    )
    reply.add_argument(
        '--file',
        type=str,
        required=False,
        help='Send file as responds. If "-", read from stdin'
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
        default=config["default_author"],
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
        required=False,
        default=config["default_voter"],
        help='The voter account name'
    )
    parser_upvote.add_argument(
        '--weight',
        type=float,
        default=config["default_vote_weight"],
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
        default=config["default_voter"],
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
        default=config["default_vote_weight"],
        required=False,
        help='Actual weight (from 0.1 to 100.0)'
    )

    """
        Command "replies"
    """
    replies = subparsers.add_parser('replies', help='Show recent replies to your posts')
    replies.set_defaults(command="replies")
    replies.add_argument(
        '--author',
        type=str,
        required=False,
        default=config["default_author"],
        help='Show replies to this author'
    )
    replies.add_argument(
        '--limit',
        type=int,
        default=config["limit"],
        help='Limit posts by number'
    )

    """
        Command "transfer"
    """
    parser_transfer = subparsers.add_parser('transfer', help='Transfer STEEM')
    parser_transfer.set_defaults(command="transfer")
    parser_transfer.add_argument(
        'to',
        type=str,
        help='Recepient'
    )
    parser_transfer.add_argument(
        'amount',
        type=float,
        help='Amount to transfer'
    )
    parser_transfer.add_argument(
        'asset',
        type=str,
        choices=["STEEM", "SBD"],
        help='Asset to (i.e. STEEM or SDB)'
    )
    parser_transfer.add_argument(
        'memo',
        type=str,
        nargs="?",
        default="",
        help='Optional memo'
    )
    parser_transfer.add_argument(
        '--account',
        type=str,
        required=False,
        default=config["default_author"],
        help='Transfer from this account'
    )

    """
        Command "powerup"
    """
    parser_powerup = subparsers.add_parser('powerup', help='Power up (vest STEEM as STEEM POWER)')
    parser_powerup.set_defaults(command="powerup")
    parser_powerup.add_argument(
        'amount',
        type=str,
        help='Amount to powerup including asset (e.g.: 100.000 STEEM)'
    )
    parser_powerup.add_argument(
        '--account',
        type=str,
        required=False,
        default=config["default_author"],
        help='Powerup from this account'
    )
    parser_powerup.add_argument(
        '--to',
        type=str,
        required=False,
        default=config["default_author"],
        help='Powerup this account'
    )

    """
        Command "powerdown"
    """
    parser_powerdown = subparsers.add_parser('powerdown', help='Power down (start withdrawing STEEM from STEEM POWER)')
    parser_powerdown.set_defaults(command="powerdown")
    parser_powerdown.add_argument(
        'amount',
        type=str,
        help='Amount to powerdown including asset (e.g.: 100.000 VESTS)'
    )
    parser_powerdown.add_argument(
        '--account',
        type=str,
        required=False,
        default=config["default_author"],
        help='powerdown from this account'
    )

    """
        Command "powerdownroute"
    """
    parser_powerdownroute = subparsers.add_parser('powerdownroute', help='Setup a powerdown route')
    parser_powerdownroute.set_defaults(command="powerdownroute")
    parser_powerdownroute.add_argument(
        'to',
        type=str,
        default=config["default_author"],
        help='The account receiving either VESTS/SteemPower or STEEM.'
    )
    parser_powerdownroute.add_argument(
        '--percentage',
        type=float,
        default=100,
        help='The percent of the withdraw to go to the "to" account'
    )
    parser_powerdownroute.add_argument(
        '--account',
        type=str,
        default=config["default_author"],
        help='The account which is powering down'
    )
    parser_powerdownroute.add_argument(
        '--auto_vest',
        action='store_true',
        help=('Set to true if the from account should receive the VESTS as'
              'VESTS, or false if it should receive them as STEEM.')
    )

    """
        Command "balance"
    """
    parser_balance = subparsers.add_parser('balance', help='Show the balance of one more more accounts')
    parser_balance.set_defaults(command="balance")
    parser_balance.add_argument(
        'account',
        type=str,
        nargs="*",
        default=config["default_author"],
        help='balance of these account (multiple accounts allowed)'
    )

    """
        Command "history"
    """
    parser_history = subparsers.add_parser('history', help='Show the history of an account')
    parser_history.set_defaults(command="history")
    parser_history.add_argument(
        'account',
        type=str,
        nargs="?",
        default=config["default_author"],
        help='History of this account'
    )
    parser_history.add_argument(
        '--limit',
        type=int,
        default=config["limit"],
        help='Limit number of entries'
    )
    parser_history.add_argument(
        '--end',
        type=int,
        default=99999999999999,
        help='Transactioon numer (#) of the last transaction to show.'
    )
    parser_history.add_argument(
        '--types',
        type=str,
        nargs="*",
        default=[],
        help='Show only these operation types'
    )

    """
        Command "interest"
    """
    interest = subparsers.add_parser('interest', help='Get information about interest payment')
    interest.set_defaults(command="interest")
    interest.add_argument(
        'account',
        type=str,
        nargs="*",
        default=config["default_author"],
        help='Inspect these accounts'
    )

    """
        Command "web"
    """
    webconfig = subparsers.add_parser('web', help='Launch web version of piston')
    webconfig.set_defaults(command="web")
    webconfig.add_argument(
        '--port',
        type=int,
        default=config["web:port"],
        help='Port to open for internal web requests'
    )
    webconfig.add_argument(
        '--host',
        type=str,
        default=config["web:host"],
        help='Host address to listen to'
    )

    """
        Parse Arguments
    """
    args = parser.parse_args()

    # Logging
    log = logging.getLogger("piston")
    verbosity = ["critical",
                 "error",
                 "warn",
                 "info",
                 "debug"][int(min(args.verbose, 4))]
    log.setLevel(getattr(logging, verbosity.upper()))
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch = logging.StreamHandler()
    ch.setLevel(getattr(logging, verbosity.upper()))
    ch.setFormatter(formatter)
    log.addHandler(ch)

    # GrapheneAPI logging
    if args.verbose > 4:
        verbosity = ["critical",
                     "error",
                     "warn",
                     "info",
                     "debug"][int(min((args.verbose - 4), 4))]
        gphlog = logging.getLogger("graphenebase")
        gphlog.setLevel(getattr(logging, verbosity.upper()))
        gphlog.addHandler(ch)
    if args.verbose > 8:
        verbosity = ["critical",
                     "error",
                     "warn",
                     "info",
                     "debug"][int(min((args.verbose - 8), 4))]
        gphlog = logging.getLogger("grapheneapi")
        gphlog.setLevel(getattr(logging, verbosity.upper()))
        gphlog.addHandler(ch)

    if not hasattr(args, "command"):
        parser.print_help()
        sys.exit(2)

    # We don't require RPC for these commands
    rpc_not_required = [
        "set",
        "config",
        "web"
        ""]
    if args.command not in rpc_not_required and args.command:
        steem = Steem(
            node=args.node,
            rpcuser=args.rpcuser,
            rpcpassword=args.rpcpassword,
            nobroadcast=args.nobroadcast,
        )

    if args.command == "set":
        config[args.key] = args.value

    elif args.command == "config":
        t = PrettyTable(["Key", "Value"])
        t.align = "l"
        for key in config:
            if key in availableConfigurationKeys:  # hide internal config data
                t.add_row([key, config[key]])
        print(t)

    elif args.command == "changewalletpassphrase":
        steem.wallet.changePassphrase()

    elif args.command == "addkey":
        pub = None
        if len(args.wifkeys):
            for wifkey in args.wifkeys:
                pub = (steem.wallet.addPrivateKey(wifkey))
                if pub:
                    print(pub)
        else:
            import getpass
            wifkey = ""
            while True:
                wifkey = getpass.getpass('Private Key (wif) [Enter to quit]:')
                if not wifkey:
                    break
                pub = (steem.wallet.addPrivateKey(wifkey))
                if pub:
                    print(pub)

        if pub:
            name = steem.wallet.getAccountFromPublicKey(pub)
            print("Setting new default user: %s" % name)
            print("You can change these settings with:")
            print("    piston set default_author x")
            print("    piston set default_voter x")
            config["default_author"] = name
            config["default_voter"] = name

    elif args.command == "delkey":
        for pub in args.pub:
            steem.wallet.removePrivateKeyFromPublicKey(pub)

    elif args.command == "getkey":
        print(steem.wallet.getPrivateKeyForPublicKey(args.pub))

    elif args.command == "listkeys":
        t = PrettyTable(["Available Key"])
        t.align = "l"
        for key in steem.wallet.getPublicKeys():
            t.add_row([key])
        print(t)

    elif args.command == "listaccounts":
        t = PrettyTable(["Name", "Type", "Available Key"])
        t.align = "l"
        for account in steem.wallet.getAccounts():
            t.add_row([
                account["name"] or "n/a",
                account["type"] or "n/a",
                account["pubkey"]
            ])
        print(t)

    elif args.command == "reply":
        from textwrap import indent
        parent = steem.get_content(args.replyto)
        if parent["id"] == "0.0.0":
            print("Can't find post %s" % args.replyto)
            return

        reply_message = indent(parent["body"], "> ")

        post = frontmatter.Post(reply_message, **{
            "title": args.title if args.title else "Re: " + parent["title"],
            "author": args.author if args.author else "required",
            "replyto": args.replyto,
        })

        meta, json_meta, message = yaml_parse_file(args, initial_content=post)

        for required in ["author", "title"]:
            if (required not in meta or
                    not meta[required] or
                    meta[required] == "required"):
                print("'%s' required!" % required)
                # TODO, instead of terminating here, send the user back
                # to the EDITOR
                return

        pprint(steem.reply(
            meta["replyto"],
            message,
            title=meta["title"],
            author=meta["author"],
            meta=json_meta,
        ))

    elif args.command == "post" or args.command == "yaml":
        post = frontmatter.Post("", **{
            "title": args.title if args.title else "required",
            "author": args.author if args.author else "required",
            "category": args.category if args.category else "required",
        })

        meta, json_meta, body = yaml_parse_file(args, initial_content=post)

        if not body:
            print("Empty body! Not posting!")
            return

        for required in ["author", "title", "category"]:
            if (required not in meta or
                    not meta[required] or
                    meta[required] == "required"):
                print("'%s' required!" % required)
                # TODO, instead of terminating here, send the user back
                # to the EDITOR
                return

        pprint(steem.post(
            meta["title"],
            body,
            author=meta["author"],
            category=meta["category"],
            meta=json_meta,
        ))

    elif args.command == "edit":
        original_post = steem.get_content(args.post)

        edited_message = None
        if original_post["id"] == "0.0.0":
            print("Can't find post %s" % args.post)
            return

        post = frontmatter.Post(original_post["body"], **{
            "title": original_post["title"] + " (immutable)",
            "author": original_post["author"] + " (immutable)"
        })

        meta, json_meta, edited_message = yaml_parse_file(args, initial_content=post)
        pprint(steem.edit(
            args.post,
            edited_message,
            replace=args.replace,
            meta=json_meta,
        ))

    elif args.command == "upvote" or args.command == "downvote":
        if args.command == "downvote":
            weight = -float(args.weight)
        else:
            weight = +float(args.weight)
        if not args.voter:
            print("Not voter provided!")
            return
        pprint(steem.vote(
            args.post,
            weight,
            voter=args.voter
        ))

    elif args.command == "read":
        post_author, post_permlink = resolveIdentifier(args.post)

        if args.parents:
            # FIXME inconsistency, use @author/permlink instead!
            dump_recursive_parents(
                steem.rpc,
                post_author,
                post_permlink,
                args.parents,
                format=args.format
            )

        if not args.comments and not args.parents:
            post = steem.get_content(args.post)

            if post["id"] == "0.0.0":
                print("Can't find post %s" % args.post)
                return
            if args.format == "markdown":
                body = markdownify(post["body"])
            else:
                body = post["body"]

            if args.full:
                meta = {}
                for key in post:
                    if key in ["steem", "body"]:
                        continue
                    meta[key] = post[key]
                yaml = frontmatter.Post(body, **meta)
                print(frontmatter.dumps(yaml))
            else:
                print(body)

        if args.comments:
            dump_recursive_comments(
                steem.rpc,
                post_author,
                post_permlink,
                format=args.format
            )

    elif args.command == "categories":
        categories = steem.get_categories(
            sort=args.sort,
            begin=args.category,
            limit=args.limit
        )
        print(args.sort)
        print(args.category)
        print(args.limit)
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
        list_posts(
            steem.get_posts(
                limit=args.limit,
                sort=args.sort,
                category=args.category,
                start=args.start
            )
        )

    elif args.command == "replies":
        if not args.author:
            print("Please specify an author via --author\n "
                  "or define your default author with:\n"
                  "   piston set default_author x")
        else:
            discussions = steem.get_replies(args.author)
            list_posts(discussions[0:args.limit])

    elif args.command == "transfer":
        pprint(steem.transfer(
            args.to,
            args.amount,
            args.asset,
            memo=args.memo,
            account=args.account
        ))

    elif args.command == "powerup":
        pprint(steem.transfer_to_vesting(
            args.amount,
            account=args.account,
            to=args.to
        ))

    elif args.command == "powerdown":
        pprint(steem.withdraw_vesting(
            args.amount,
            account=args.account,
        ))

    elif args.command == "powerdownroute":
        pprint(steem.set_withdraw_vesting_route(
            args.to,
            percentage=args.percentage,
            account=args.account,
            auto_vest=args.auto_vest
        ))

    elif args.command == "balance":
        t = PrettyTable(["Account", "STEEM", "SBD", "VESTS", "VESTS (in STEEM)"])
        t.align = "r"
        if isinstance(args.account, str):
            args.account = [args.account]
        for a in args.account:
            b = steem.get_balances(a)
            t.add_row([
                a,
                b["balance"],
                b["sbd_balance"],
                b["vesting_shares"],
                b["vesting_shares_steem"]
            ])
        print(t)

    elif args.command == "history":
        import json
        t = PrettyTable(["#", "time/block", "Operation", "Details"])
        t.align = "r"
        if isinstance(args.account, str):
            args.account = [args.account]
        if isinstance(args.types, str):
            args.types = [args.types]

        for a in args.account:
            for b in steem.loop_account_history(
                a,
                args.end,
                limit=args.limit,
                only_ops=args.types
            ):
                t.add_row([
                    b[0],
                    "%s (%s)" % (b[1]["timestamp"], b[1]["block"]),
                    b[1]["op"][0],
                    format_operation_details(b[1]["op"]),
                ])
        print(t)

    elif args.command == "interest":
        t = PrettyTable(["Account",
                         "Last Interest Payment",
                         "Next Payment",
                         "Interest rate",
                         "Interest"])
        t.align = "r"
        if isinstance(args.account, str):
            args.account = [args.account]
        for a in args.account:
            i = steem.interest(a)

            t.add_row([
                a,
                i["last_payment"],
                i["next_payment"],
                "%.1f%%" % i["interest_rate"],
                "%.3f SBD" % i["interest"],
            ])
        print(t)

    elif args.command == "web":
        from .web_steem import WebSteem
        # WebSteem is a static class that ensures that
        # the steem connection is a singelton
        WebSteem(args.node,
                 args.rpcuser,
                 args.rpcpassword,
                 args.nobroadcast)
        from . import web
        web.run(port=args.port, host=args.host)

    else:
        print("No valid command given")


args = None

if __name__ == '__main__':
    main()
