import warnings
from steem.wallet import Wallet as WalletSteem
warnings.simplefilter('default')


class Wallet(WalletSteem):
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "Please replace 'import piston.wallet' by 'import steem.wallet'",
            DeprecationWarning
        )
        super(Wallet, self).__init__(*args, **kwargs)
