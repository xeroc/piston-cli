import sys
import json
from prettytable import PrettyTable, ALL as allBorders
from textwrap import fill, TextWrapper
import frontmatter
import re
from piston.storage import configStorage as config
from piston.utils import constructIdentifier
from piston import steem as stm

# For recursive display of a discussion thread (--comments + --parents)
currentThreadDepth = 0


class UIError(Exception):
    pass


def markdownify(t):
    width = 120

    def mdCodeBlock(t):
        return ("    " +
                Back.WHITE +
                Fore.BLUE +
                "   " +
                t.group(1) +
                "   " +
                Fore.RESET +
                Back.RESET)

    def mdCodeInline(t):
        return (Back.WHITE +
                Fore.BLUE +
                " " +
                t.group(1) +
                " " +
                Fore.RESET +
                Back.RESET)

    def mdList(t):
        return (Fore.GREEN +
                " " +
                t.group(1) +
                " " +
                Fore.RESET +
                t.group(2))

    def mdLink(t):
        return (Fore.RED +
                "[%s]" % t.group(1) +
                Fore.GREEN +
                "(%s)" % t.group(2) +
                Fore.RESET)

    def mdHeadline(t):
        colors = [
            Back.RED,
            Back.GREEN,
            Back.YELLOW,
            Back.BLUE,
            Back.MAGENTA,
            Back.CYAN,
        ]
        color = colors[len(t.group(1)) % len(colors)]
        # width = 80 - 15 * len(t.group(1))
        headline = (color +
                    '{:^{len}}'.format(t.group(2), len=width) +
                    Back.RESET)
        return (Style.BRIGHT +
                headline +
                Style.NORMAL)

    def mdBold(t):
        return (Style.BRIGHT +
                t.group(1) +
                Style.NORMAL)

    def mdLight(t):
        return (Style.DIM +
                t.group(1) +
                Style.NORMAL)

    def wrapText(t):
        postWrapper = TextWrapper()
        postWrapper.width = width
        return ("\n".join(postWrapper.fill(l) for l in t.splitlines()))

    import colorama
    from colorama import Fore, Back, Style
    colorama.init()

    t = re.sub(r"\n\n", "{NEWLINE}", t, flags=re.M)
    t = re.sub(r"\n(^[^#\-\*].*)", r"\1", t, flags=re.M)
    t = re.sub(r"{NEWLINE}", "\n\n", t, flags=re.M)

    t = re.sub(r"\*\*(.*)\*\*", mdBold, t, flags=re.M)
    t = re.sub(r"\*(.*)\*", mdLight, t, flags=re.M)

    t = re.sub(r"`(.*)`", mdCodeInline, t, flags=re.M)
    t = re.sub(r"^ {4,}(.*)", mdCodeBlock, t, flags=re.M)
    t = re.sub(r"^([\*\-])\s*(.*)", mdList, t, flags=re.M)
    t = re.sub(r"\[(.*)\]\((.*)\)", mdLink, t, flags=re.M)

    t = wrapText(t)

    t = re.sub(r"^(#+)\s*(.*)$", mdHeadline, t, flags=re.M)
    t = re.sub(r"```(.*)```", mdCodeBlock, t, flags=re.M)

    return t


def __get_text_wrapper(width=60):
    """
    Get text wrapper with a fixed with.

    :param width: width of the wrapper. Default 60.
    :return: text wrapper
    :rtype: :py:class:`TextWrapper`
    """
    wrapper = TextWrapper()
    wrapper.width = width
    wrapper.subsequent_indent = " "

    return wrapper


def list_posts(discussions, custom_columns=None):
    """
    List posts using PrettyTable. Use default layout if custom column list
    is not specified. Default layout is [ "identifier", "title", "category",
    "replies", "votes", "payouts"]. Custom layout can contain one or more
    allowed columns and rows always start with [ "identifier", "title" ].

    :param discussions: discussions (posts) list
    :type discussions: list
    :param custom_columns: custom columns to display
    :type custom_columns: list

    :raises: :py:class:`UIError`: If tried to use wrong column(s).
    """
    if not discussions:
        return
    if not custom_columns:
        t = PrettyTable([
            "identifier",
            "title",
            "category",
            "replies",
            # "votes",
            "payouts",
        ])
        t.align = "l"
        t.align["payouts"] = "r"
        # t.align["votes"] = "r"
        t.align["replies"] = "c"
        for d in discussions:
            # Some discussions are dicts or identifiers
            if isinstance(d, str):
                d = discussions[d]
            identifier = constructIdentifier(d["author"], d["permlink"])
            identifier_wrapper = __get_text_wrapper()
            row = [
                identifier_wrapper.fill(identifier),
                identifier_wrapper.fill(d["title"]),
                d["category"],
                d["children"],
                # d["net_rshares"],
                d["pending_payout_value"],
            ]
            t.add_row(row)
    else:
        available_attrs = set(vars(discussions[0]))
        if not set(custom_columns).issubset(available_attrs):
            wrong_columns = set(custom_columns).difference(available_attrs)
            raise UIError("Please use allowed column names only: %s. "
                          "Error caused by %s." %
                          (sorted(available_attrs), wrong_columns))
        # move identifier and title to front if available
        for c in ["title", "identifier"]:
            if c in custom_columns:
                custom_columns.insert(0, custom_columns.pop(
                    custom_columns.index(c)))
        t = PrettyTable(custom_columns)
        t.align = "l"
        for d in discussions:
            display_columns = custom_columns.copy()
            if isinstance(d, str):
                d = discussions[d]
            identifier = constructIdentifier(d["author"], d["permlink"])
            identifier_wrapper = __get_text_wrapper()
            row = []
            # identifier and title always go first if available
            if "identifier" in display_columns:
                row.append(identifier_wrapper.fill(identifier))
                display_columns.remove("identifier")
            if "title" in display_columns:
                row.append(identifier_wrapper.fill(d["title"]))
                display_columns.remove("title")
            for column in display_columns:
                row.append(d[column])
            if row:
                t.add_row(row)
    print(t)


def dump_recursive_parents(rpc,
                           post_author,
                           post_permlink,
                           limit=1,
                           format="markdown"):
    global currentThreadDepth

    limit = int(limit)

    postWrapper = TextWrapper()
    postWrapper.width = 120
    postWrapper.initial_indent = "  " * (limit)
    postWrapper.subsequent_indent = "  " * (limit)

    if limit > currentThreadDepth:
        currentThreadDepth = limit + 1

    post = rpc.get_content(post_author, post_permlink)

    if limit and post["parent_author"]:
        parent = rpc.get_content_replies(post["parent_author"], post["parent_permlink"])
        if len(parent):
            dump_recursive_parents(rpc, post["parent_author"], post["parent_permlink"], limit - 1)

    meta = {}
    for key in ["author", "permlink"]:
        meta[key] = post[key]
    meta["reply"] = "@{author}/{permlink}".format(**post)
    if format == "markdown":
        body = markdownify(post["body"])
    else:
        body = post["body"]
    yaml = frontmatter.Post(body, **meta)
    print(frontmatter.dumps(yaml))


def dump_recursive_comments(rpc,
                            post_author,
                            post_permlink,
                            depth=0,
                            format="markdown"):
    global currentThreadDepth
    postWrapper = TextWrapper()
    postWrapper.width = 120
    postWrapper.initial_indent = "  " * (depth + currentThreadDepth)
    postWrapper.subsequent_indent = "  " * (depth + currentThreadDepth)

    depth = int(depth)

    posts = rpc.get_content_replies(post_author, post_permlink)
    for post in posts:
        meta = {}
        for key in ["author", "permlink"]:
            meta[key] = post[key]
        meta["reply"] = "@{author}/{permlink}".format(**post)
        if format == "markdown":
            body = markdownify(post["body"])
        else:
            body = post["body"]
        yaml = frontmatter.Post(body, **meta)
        print(frontmatter.dumps(yaml))
        reply = rpc.get_content_replies(post["author"], post["permlink"])
        if len(reply):
            dump_recursive_comments(rpc, post["author"], post["permlink"], depth + 1)


def format_operation_details(op, memos=False):
    if op[0] == "vote":
        return "%s: %s" % (
            op[1]["voter"],
            constructIdentifier(op[1]["author"], op[1]["permlink"])
        )
    elif op[0] == "comment":
        return "%s: %s" % (
            op[1]["author"],
            constructIdentifier(op[1]["author"], op[1]["permlink"])
        )
    elif op[0] == "transfer":
        str_ = "%s -> %s %s" % (
            op[1]["from"],
            op[1]["to"],
            op[1]["amount"],
        )

        if memos:
            memo = op[1]["memo"]
            if len(memo) > 0 and memo[0] == "#":
                steem = stm.Steem()
                # memo = steem.decode_memo(memo, op[1]["from"])
                memo = steem.decode_memo(memo, op)
            str_ += " (%s)" % memo
        return str_
    elif op[0] == "interest":
        return "%s" % (
            op[1]["interest"]
        )
    else:
        return json.dumps(op[1], indent=4)


def confirm(question, default="yes"):
    """ Confirmation dialog that requires *manual* input.

        :param str question: Question to ask the user
        :param str default: default answer
        :return: Choice of the user
        :rtype: bool

    """
    valid = {"yes": True, "y": True, "ye": True,
             "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)
    while True:
        sys.stdout.write(question + prompt)
        choice = input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "
                             "(or 'y' or 'n').\n")


def print_permissions(account):
    t = PrettyTable(["Permission", "Threshold", "Key/Account"], hrules=allBorders)
    t.align = "r"
    for permission in ["owner", "active", "posting"]:
        auths = []
        for type_ in ["account_auths", "key_auths"]:
            for authority in account[permission][type_]:
                auths.append("%s (%d)" % (authority[0], authority[1]))
        t.add_row([
            permission,
            account[permission]["weight_threshold"],
            "\n".join(auths),
        ])
    print(t)


def get_terminal(text="Password", confirm=False, allowedempty=False):
    import getpass
    while True:
        pw = getpass.getpass(text)
        if not pw and not allowedempty:
            print("Cannot be empty!")
            continue
        else:
            if not confirm:
                break
            pwck = getpass.getpass(
                "Confirm " + text
            )
            if (pw == pwck):
                break
            else:
                print("Not matching!")
    return pw
