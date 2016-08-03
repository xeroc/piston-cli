from .steem import Steem, Post
from .storage import configStorage as configStore
import logging
log = logging.getLogger(__name__)


class WebSteem(object):

    #: The static steem connection
    steem = None

    def __init__(
        self,
        node=configStore["node"],
        rpcuser=configStore["rpcuser"],
        rpcpassword=configStore["rpcpass"],
        nobroadcast=configStore["web:nobroadcast"],
        num_retries=1  # do at least 1 retry in the case the connection was lost
    ):
        """ This class is a singelton and makes sure that only one
            connection to the Steem node is established and shared among
            flask threads.
        """
        if not WebSteem.steem:
            self.connect(node,
                         rpcuser,
                         rpcpassword,
                         nobroadcast,
                         num_retries)

    def getSteem(self):
        return WebSteem.steem

    def connect(
        self,
        node=configStore["node"],
        rpcuser=configStore["rpcuser"],
        rpcpassword=configStore["rpcpass"],
        nobroadcast=configStore["web:nobroadcast"],
        num_retries=1  # do at least 1 retry in the case the connection was lost
    ):
        log.debug("trying to connect to %s" % configStore["node"])
        try:
            WebSteem.steem = Steem(
                node=node,
                rpcuser=rpcuser,
                rpcpassword=rpcpassword,
                nobroadcast=nobroadcast,
                num_retries=num_retries,
            )
        except:
            print("=" * 80)
            print(
                "No connection to %s could be established!\n" % configStore["node"] +
                "Please try again later, or select another node via:\n"
                "    piston node wss://example.com"
            )
            print("=" * 80)
            exit(1)
