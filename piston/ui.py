import json
from prettytable import PrettyTable
from textwrap import fill, TextWrapper
import frontmatter
import re
from .storage import configStorage as config
from .utils import constructIdentifier

# For recursive display of a discussion thread (--comments + --parents)
currentThreadDepth = 0


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


def list_posts(discussions):
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

        identifier = "@%s/%s" % (d["author"], d["permlink"])
        identifier_wrapper = TextWrapper()
        identifier_wrapper.width = 60
        identifier_wrapper.subsequent_indent = " "

        t.add_row([
            identifier_wrapper.fill(identifier),
            identifier_wrapper.fill(d["title"]),
            d["category"],
            d["children"],
            # d["net_rshares"],
            d["pending_payout_value"],
        ])
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


def format_operation_details(op):
    if op[0] == "vote":
        return "%s: %s" % (
            op[1]["voter"],
            constructIdentifier(op[1]["author"], op[1]["permlink"])
        )
    if op[0] == "comment":
        return "%s: %s" % (
            op[1]["author"],
            constructIdentifier(op[1]["author"], op[1]["permlink"])
        )
    if op[0] == "transfer":
        return "%s -> %s %s (%s)" % (
            op[1]["from"],
            op[1]["to"],
            op[1]["amount"],
            op[1]["memo"],
        )
    else:
        return json.dumps(op[1])
