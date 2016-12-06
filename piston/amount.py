import warnings
from steem.amount import Amount as AmountSteem


class Amount(AmountSteem):
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "[DeprecationWarning] Please replace 'import piston.amount' by 'import steem.amount'"
        )
        super(Amount, self).__init__(*args, **kwargs)
