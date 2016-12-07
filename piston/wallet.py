import warnings
from steem.wallet import Wallet as WalletSteem


class Wallet(WalletSteem):
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "[DeprecationWarning] Please replace 'import piston.wallet' by 'import steem.wallet'"
        )
        super(Wallet, self).__init__(*args, **kwargs)
