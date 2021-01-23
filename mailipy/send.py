#!/usr/bin/env python3

import argparse
import email
import getpass
import os
import shutil
import smtplib
import ssl
import sys


def main():
    parser = argparse.ArgumentParser(description="Bulk send emails from the 'outbox' folder.")
    parser.add_argument("server", help="the URL of the SMTP server, including the port")
    parser.add_argument("username", help="the username to login on the mail server")
    parser.add_argument("outbox", help="the folder where to access the emails that should be sent")
    parser.add_argument("sent", nargs="?", default="sent", help="the folder where to move the emails sent (default: sent)")
    parser.add_argument("--continue", help="continue sending, even if the 'sent' folder is not empty", action="store_true", dest="continue_")
    args = parser.parse_args()

    if (not os.path.isdir(args.outbox)) or len(os.listdir(args.outbox)) == 0:
        print("The outbox folder should contain some emails!")
        sys.exit(1)

    # FIXME: skip the check if --continue was specified... but actually we should still check that: 'sent' is a directory AND it doesn't contain files which also exist in 'outbox'
    if not args.continue_:
        if os.path.exists(args.sent) and ((not os.path.isdir(args.sent)) or len(os.listdir(args.sent)) > 0):
            print("The sent folder should be an empty folder, or not exist at all!")
            sys.exit(1)

    host, port = args.server.split(":")
    port = int(port)

    emails = os.listdir(args.outbox)

    if any((not os.path.isfile(os.path.join(args.outbox, eml))) or (not eml.lower().endswith(".eml")) for eml in emails):
        print("The outbox folder contains invalid files!")
        sys.exit(1)

    print("You are about to send %d emails." % len(emails))
    password = getpass.getpass("Password for %s@%s: " % (args.username, args.server))

    context=ssl.create_default_context()
    with smtplib.SMTP_SSL(host, port, context=context) as server:
        server.login(args.username, password)

        # Create sent folder if necessary
        if not os.path.exists(args.sent):
            os.mkdir(args.sent)

        for eml in emails:
            msg = email.message_from_file(open(os.path.join(args.outbox, eml)))
            try:
                rcpt = [msg["To"]]
                extra = []
                if "Cc" in msg:
                    rcpt += msg["Cc"].split(", ")
                    extra += ["cc: " + msg["Cc"]]
                if "Bcc" in msg:
                    rcpt += msg["Bcc"].split(", ")
                    extra += ["bcc: " + msg["Bcc"]]
                if extra:
                    extra = " (%s)" % " | ".join(extra)
                else:
                    extra = ""
                print("Sending email to %s%s..." % (msg["To"], extra))
                server.sendmail(msg["From"], rcpt, msg.as_string())

                # On success, move the message from the outbox to the sent folder
                shutil.move(os.path.join(args.outbox, eml), os.path.join(args.sent, eml))
            except:
                print("[!] Error when sending email to %s" % (msg["To"]))


if __name__ == "__main__":
    main()
