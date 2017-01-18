import warnings
from steem.post import Post as PostSteem
from steem.post import (
    VotingInvalidOnArchivedPost
)
warnings.simplefilter('default')


class Post(PostSteem):
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "Please replace 'import piston.post' by 'import steem.post'",
            DeprecationWarning
        )
        super(Post, self).__init__(*args, **kwargs)
