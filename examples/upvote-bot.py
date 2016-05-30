from piston.steem import Steem
import os
import json
steem = Steem(wif=os.environ["WIF"])
authors = json.loads(os.environ["AUTHORS"])
for c in steem.stream_comments(mode="head"):
    if c["author"] in authors:
        print(c.upvote())
