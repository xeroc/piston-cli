import warnings
from steem.post import Post as PostSteem
from steem.post import (
    VotingInvalidOnArchivedPost
)


class Post(PostSteem):
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "[DeprecationWarning] Please replace 'import piston.post' by 'import steem.post'"
        )
        super(Post, self).__init__(*args, **kwargs)
