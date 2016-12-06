import warnings
from steem.aes import AESCipher as AESCipherSteem


class AESCipher(AESCipherSteem):
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "[DeprecationWarning] Please replace 'import piston.aes' by 'import steem.aes'"
        )
        super(AESCipher, self).__init__(*args, **kwargs)
