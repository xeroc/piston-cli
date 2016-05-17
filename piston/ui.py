from prettytable import PrettyTable
from textwrap import fill, TextWrapper
import frontmatter
from piston.configuration import Configuration
config = Configuration()

# For recursive display of a discussion thread (--comments + --parents)
currentThreadDepth = 0


def list_posts(discussions):
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
            identifier_wrapper = TextWrapper()
            identifier_wrapper.width = 60
            identifier_wrapper.subsequent_indent = " "

            t.add_row([
                identifier_wrapper.fill(identifier),
                identifier_wrapper.fill(d["title"]),
                d["category"],
                d["children"],
                d["net_rshares"],
                d["pending_payout_value"],
            ])
        print(t)


def dump_recursive_parents(rpc, post_author, post_permlink, limit=1):
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
    yaml = frontmatter.Post(post["body"], **meta)
    d = frontmatter.dumps(yaml)
    print("\n".join(postWrapper.fill(l) for l in d.splitlines()))


def dump_recursive_comments(rpc, post_author, post_permlink, depth=0):
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
        yaml = frontmatter.Post(post["body"], **meta)
        d = frontmatter.dumps(yaml)
        print("\n".join(postWrapper.fill(l) for l in d.splitlines()))
        reply = rpc.get_content_replies(post["author"], post["permlink"])
        if len(reply):
            dump_recursive_comments(rpc, post["author"], post["permlink"], depth + 1)
