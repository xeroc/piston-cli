from PySide.QtCore import *
from PySide.QtGui import *
from steemapi.steemnoderpc import SteemNodeRPC
from steembase import transactions
import sys
from ui_steem import Ui_MainWindow
from pprint import pprint
from markdown import markdown as md
import pymdownx
import re

import content
from settings import Settings
from steemposts import SteemPostItem, SteemPostModel
from steemaccounts import SteemAccountsModel
from steempoststate import SteemPostStateModel


def markdownSyntax(t):
    return md(t, extensions=['markdown.extensions.extra',
                             'markdown.extensions.toc',
                             'markdown.extensions.admonition',
                             ])


class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        global rpc

        self.setupUi(self)
        self.connectApiServer()

        self.resize(800, 400)
        self.postsModel = SteemPostModel(rpc)
        self.postList.setAlternatingRowColors(True)
        self.postList.setModel(self.postsModel)

        self.postSelectionModel = self.postList.selectionModel()

        # Slots
        self.postSelectionModel.selectionChanged.connect(self.openPost)
        self.websocketUrl.editingFinished.connect(self.connectApiServer)
        self.replyButton.clicked.connect(self.sendReply)
        self.downVoteButton.clicked.connect(self.downVotePost)
        self.upVoteButton.clicked.connect(self.upVotePost)
        self.addPrivateKeyBtn.clicked.connect(self.addPrivateKey)
        self.deleteSelectedKey.clicked.connect(self.removePrivateKey)

        self.postTitle.textEdited.connect(self.postTitleChanged)

        debug = True

        if debug:
            self.settings = Settings("password", rpc)
        else:
            while True:
                if Settings.exists():
                    password, ok = QInputDialog.getText(
                        self, self.tr("Enter Password"),
                        self.tr("Password:"),
                        QLineEdit.Password,
                    )
                else:
                    password, ok = QInputDialog.getText(
                        self, self.tr("Enter Password"),
                        self.tr("Password:"),
                        QLineEdit.Password,
                    )
                    password2, ok = QInputDialog.getText(
                        self, self.tr("Enter Password"),
                        self.tr("Re-type Password:"),
                        QLineEdit.Password,
                    )
                    if password != password2:
                        continue
                if ok and password:
                    try:
                        self.settings = Settings(password, rpc)
                        self.settings.storeprivkeys()
                        break
                    except:
                        continue
                else:
                    sys.exit()

        self.accountsModel = SteemAccountsModel(self, self.settings)
        self.accountList.setModel(self.accountsModel)

        self.activeAccount.setModel(self.accountsModel)
        self.activeAccount.setModelColumn(0)

        # timer = QTimer(self)
        # self.connect(timer, SIGNAL("timeout()"), self.reloadMessages)
        # timer.start(15 * 1000)

    def reloadMessages(self):
        self.statusMessage("Updated Messages")
        self.postsModel.loadMessages()

    def urlify(self, s):
        s = re.sub(r"[^\w\s]", '', s)
        s = re.sub(r"\s+", '-', s)
        return s

    def postTitleChanged(self):
        if self.postPermlink.text() == "":
            self.postPermlink.setText("")
        if self.postPermlink.text() == self.urlify(self.postTitle.text())[:-1]:
            self.postPermlink.setText(self.urlify(self.postTitle.text()))

    def loadAccounts(self):
        for key in self.settings.getPublicKeys():
            self.accountsModel.insertRow(self.accountsModel.rowCount(), QStandardItem([key]))

    def removePrivateKey(self):
        for s in self.accountList.selectionModel().selectedIndexes():
            self.accountsModel.removeKey(s)

    def addPrivateKey(self):
        if(self.accountsModel.addKey(self.addPrivateKeyText.text())):
            self.addPrivateKeyText.setText("")

    def downVotePost(self):
        self.votePost(100)

    def upVotePost(self):
        self.votePost(-100)

    def votePost(self, weight=100):
        index = self.activeAccount.currentIndex()
        voter, pub = self.accountsModel.getRow(index)
        wif = self.settings.getPrivateKeyForPublicKey(pub)
        selected = self.postSelectionModel.selectedIndexes()[0]
        message = selected.internalPointer().raw()
        expiration = transactions.formatTimeFromNow(60)
        op = transactions.Vote(
            **{"voter": voter,
               "author": message["author"],
               "permlink": message["permlink"],
               "weight": int(weight)}
        )
        ops    = [transactions.Operation(op)]
        ref_block_num, ref_block_prefix = transactions.getBlockParams(rpc)
        tx     = transactions.Signed_Transaction(ref_block_num=ref_block_num,
                                                 ref_block_prefix=ref_block_prefix,
                                                 expiration=expiration,
                                                 operations=ops)
        tx = tx.sign([wif])
        self.broadcastTx(tx)

    def sendReply(self):
        index = self.activeAccount.currentIndex()
        author, pub = self.accountsModel.getRow(index)
        wif = self.settings.getPrivateKeyForPublicKey(pub)

        index = self.postSelectionModel.selectedIndexes()
        if len(index):
            selected = index[0]
            parent = selected.internalPointer().raw()
            parent_author = parent["author"]
            parent_permlink = parent["permlink"]
        else:
            parent_author = ""
            parent_permlink = "spam"
        expiration = transactions.formatTimeFromNow(60)
        op = transactions.Comment(
            **{"parent_author": parent_author,
               "parent_permlink": parent_permlink,
               "author": author,
               "permlink": self.postPermlink.text(),
               "title": self.postTitle.text(),
               "body": self.postBody.toPlainText(),
               "json_metadata": ""}
        )
        ops    = [transactions.Operation(op)]
        ref_block_num, ref_block_prefix = transactions.getBlockParams(rpc)
        tx     = transactions.Signed_Transaction(ref_block_num=ref_block_num,
                                                 ref_block_prefix=ref_block_prefix,
                                                 expiration=expiration,
                                                 operations=ops)
        tx = tx.sign([wif])
        pprint(transactions.JsonObj(tx))
        if self.broadcastTx(tx):
            self.postPermlink.setText("")
            self.postBody.setPlainText("")
            self.postTitle.setText("")

    def broadcastTx(self, tx):
        try:
            tx     = transactions.JsonObj(tx)
            if not rpc.broadcast_transaction(tx, api="network_broadcast"):
                self.statusMessage(
                    "Successfully broadcast: {ref_block_num}/{ref_block_prefix}".format(
                        **tx
                    )
                )
                return True
            else:
                raise
        except:
            import traceback
            print(traceback.format_exc())
            self.statusMessage(
                "Error broadcasting!"
            )
        return False

    def connectApiServer(self):
        global rpc
        try:
            rpc = SteemNodeRPC(self.websocketUrl.text(), "", "")
        except Exception as e:
            QMessageBox.about(
                self,
                "Error",
                "Couldn't conenct to Server: %s" % str(e)
            )
            rpc = None

    def openPost(self, selected, deselected):
        selected = self.postSelectionModel.selectedIndexes()[0]
        message = selected.internalPointer().raw()

        self.postStateModel = SteemPostStateModel(rpc, message["author"], message["permlink"])
        self.postState.setModel(self.postStateModel)

        self.postPermlink.setText("re-{permlink}".format(**message))
        self.postTitle.setText("re: {title}".format(**message))

        fid = QFile(":/post.html")
        fid.open(QIODevice.ReadOnly | QIODevice.Text)
        post = str(fid.readAll())
        fid.close()

        for key in message:
            if key == "body":
                value = markdownSyntax(message[key])
            else:
                value = message[key]
            post = post.replace("{{%s}}" % key, str(value))
        self.webView.setHtml(str(post))

    def statusMessage(self, txt):
        self.statusBar().showMessage(self.tr(txt), 5 * 1000)

rpc = None
if __name__ == '__main__':
    app = QApplication(sys.argv)
    frame = MainWindow()
    frame.show()
    sys.exit(app.exec_())
