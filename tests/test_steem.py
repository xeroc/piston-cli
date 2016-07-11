import unittest
import piston
from piston.steem import Steem, Post

identifier = "@xeroc/piston"
testaccount = "xeroc"
wif = "5KkUHuJEFhN1RCS3GLV7UMeQ5P1k5Vu31jRgivJei8dBtAcXYMV"
steem = Steem(nobroadcast=True, wif=wif)


class Testcases(unittest.TestCase) :

    def __init__(self, *args, **kwargs):
        super(Testcases, self).__init__(*args, **kwargs)
        self.post = Post(steem, identifier)

    def test_getOpeningPost(self):
        self.post._getOpeningPost()

    def test_reply(self):
        self.post.reply(body="foobar", title="", author=testaccount, meta=None)

    def test_upvote(self):
        self.post.upvote(voter=testaccount)

    def test_downvote(self, weight=-100, voter=testaccount):
        self.post.downvote(voter=testaccount)

    def test_edit(self):
        steem.edit(identifier, "Foobar")

    def test_post(self):
        steem.post("title", "body", meta={"foo": "bar"}, author=testaccount)

    def test_create_account(self):
        steem.create_account("xeroc-create", creator=testaccount, storekeys=False)

    def test_transfer(self):
        steem.transfer(account=testaccount, to="fabian", amount="10 STEEM")

    def test_withdraw_vesting(self):
        steem.withdraw_vesting(account=testaccount, amount="10 STEEM")

    def test_transfer_to_vesting(self):
        steem.transfer_to_vesting(account=testaccount, amount="10 STEEM", to=testaccount)

    def test_get_replies(self):
        steem.get_replies(author=testaccount)

    def test_get_posts(self):
        steem.get_posts()

    def test_get_categories(self):
        steem.get_categories(sort="trending")

    def test_get_balances(self):
        steem.get_balances(testaccount)

if __name__ == '__main__':
    unittest.main()
