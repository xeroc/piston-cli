from piston.steem import Steem
from pprint import pprint

steem = Steem(nobroadcast=True)

for c in steem.stream_comments():
    pprint(vars(c))
