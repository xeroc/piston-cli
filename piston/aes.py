import warnings
from steem.aes import AESCipher as AESCipherSteem
warnings.simplefilter('default')


class AESCipher(AESCipherSteem):
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "Please replace 'import piston.aes' by 'import steem.aes'",
            DeprecationWarning
        )
        super(AESCipher, self).__init__(*args, **kwargs)
