import warnings
from steem.amount import Amount as AmountSteem
warnings.simplefilter('default')


class Amount(AmountSteem):
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "Please replace 'import piston.amount' by 'import steem.amount'",
            DeprecationWarning
        )
        super(Amount, self).__init__(*args, **kwargs)
