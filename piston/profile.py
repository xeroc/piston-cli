import warnings
from steem.profile import Profile as ProfileSteem
warnings.simplefilter('default')


class Profile(ProfileSteem):
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "Please replace 'import piston.profile' by 'import steem.profile'",
            DeprecationWarning
        )
        super(Profile, self).__init__(*args, **kwargs)
