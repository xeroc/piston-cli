import warnings
from steem.steem import Steem as SteemSteem
from steem.steem import SteemConnector as SteemConnectorSteem
from steem.steem import ExchangeConfig as ExchangeConfigSteem
from steem.post import Post as PostSteem
from steem.amount import Amount as AmountSteem


class Steem(SteemSteem):
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "[DeprecationWarning] Please replace 'import piston.steem' by 'import steem.steem'"
        )
        super(Steem, self).__init__(*args, **kwargs)


class Post(PostSteem):
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "[DeprecationWarning] Please replace 'from piston.steem import Post' by 'from steem.post import Post'"
        )
        super(Post, self).__init__(*args, **kwargs)


class Amount(AmountSteem):
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "[DeprecationWarning] Please replace 'from piston.steem import Amount' by 'from steem.amount import Amount'"
        )
        super(Amount, self).__init__(*args, **kwargs)


class SteemConnector(SteemConnectorSteem):
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "[DeprecationWarning] Please replace 'import piston.steem' by 'import steem.steem'"
        )
        super(SteemConnector, self).__init__(*args, **kwargs)


class PistonExchangeConfig(ExchangeConfigSteem):
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "[DeprecationWarning] Please replace 'import piston.steem' by 'import steem.steem'"
        )
        super(PistonExchangeConfig, self).__init__(*args, **kwargs)
