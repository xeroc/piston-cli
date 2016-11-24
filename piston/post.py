from .utils import (
    resolveIdentifier,
    constructIdentifier,
    derivePermlink,
    formatTimeString
)
import re
import json
from .amount import Amount
from datetime import datetime, timedelta


class VotingInvalidOnArchivedPost(Exception):
    pass


class Post(object):
    """ This object gets instanciated by Steem.streams and is used as an
        abstraction layer for Comments in Steem

        :param Steem steem: An instance of the Steem() object
        :param object post: The post as obtained by `get_content`
    """
    steem = None

    def __init__(self, steem, post):
        if steem.__class__.__name__ != "Steem":
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
        if not isinstance(meta, dict):
            meta = {}
        post["_tags"] = meta.get("tags", [])

        # Retrieve the root comment
        self.openingPostIdentifier, self.category = self._getOpeningPost(post)

        # Total reward
        post["total_payout_reward"] = "%.3f SBD" % (
            Amount(post.get("total_payout_value", "0 SBD")).amount +
            Amount(post.get("total_pending_payout_value", "0 SBD")).amount
        )

        # Store everything as attribute
        for key in post:
            setattr(self, key, post[key])

    def _getOpeningPost(self, post=None):
        if not post:
            post = self
        m = re.match("/([^/]*)/@([^/]*)/([^#]*).*",
                     post.get("url", ""))
        if not m:
            return "", ""
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
                Amount(x["total_payout_value"]).amount
            ), reverse=True)
        elif sort == "total_payout_reward":
            r = sorted(r, key=lambda x: float(
                Amount(x["total_payout_reward"]).amount
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
        # Test if post is archived, if so, voting is worthless but just
        # pollutes the blockchain and account history
        if getattr(self, "mode") == "archived":
            raise VotingInvalidOnArchivedPost
        return self.steem.vote(self.identifier, weight, voter=voter)
