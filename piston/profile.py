import warnings
from steem.profile import Profile as ProfileSteem


class Profile(ProfileSteem):
    def __init__(self, *args, **kwargs):
        warnings.warn(
            "[DeprecationWarning] Please replace 'import piston.profile' by 'import steem.profile'"
        )
        super(Profile, self).__init__(*args, **kwargs)
