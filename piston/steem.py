import warnings
from steem.steem import Steem as SteemSteem
from steem.post import Post as PostSteem
from steem.amount import Amount as AmountSteem
from steem.steem import AccountDoesNotExistsException
from steem.steem import (
    MissingKeyError,
    InsufficientAuthorityError
)
warnings.simplefilter('default')


class Steem(SteemSteem):
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "Please replace 'import piston.steem' by 'import steem.steem'",
            DeprecationWarning
        )
        super(Steem, self).__init__(*args, **kwargs)


class Post(PostSteem):
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "Please replace 'from piston.steem import Post' by 'from steem.post import Post'",
            DeprecationWarning
        )
        super(Post, self).__init__(*args, **kwargs)


class Amount(AmountSteem):
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "Please replace 'from piston.steem import Amount' by 'from steem.amount import Amount'",
            DeprecationWarning
        )
        super(Amount, self).__init__(*args, **kwargs)


class SteemConnector():
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "Please replace 'import piston.steem' by 'import steem.steem'",
            DeprecationWarning
        )
        raise
