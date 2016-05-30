from piston.steem import Steem
import os
import json
import sendgrid
steem = Steem()
sg = sendgrid.SendGridClient(
    os.environ['SENDGRID_USERNAME'],
    os.environ['SENDGRID_PASSWORD']
)
message = sendgrid.Mail()
addresses = {"xeroc": "mail@xeroc.org"}
# addresses = os.environ["ADDRESSES"]
for c in steem.stream_comments(start=1898900):
    for user in addresses.keys():
        if "@%s" % user in c["body"]:
            message.add_to(addresses[user])
            message.set_subject('Notification on Steem')
            message.set_text(
                "You have been messaged by %s " % (c["author"]) +
                "in the post @%s/%s" % (c["author"], c["permlink"]) +
                "\n\n" + 
                "You can read the post on Steemit.com:\n" +
                "http://steemit.com/%s/%s#@%s/%s"
                    % (c["category"],
                       c["openingPostIdentifier"],
                       c["author"], c["permlink"])
            )
            message.set_from('notify@steem')
            status, msg = sg.send(message)
            print("\nMessage sent!\n")
