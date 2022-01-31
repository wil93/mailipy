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
    parser.add_argument("--ssl", help="SSL mode to use", choices=["auto", "none", "starttls", "ssl"], default="auto")
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

    server = None
    # First try to connect with SSL (which is the most secure of the options)
    if args.ssl in ("auto", "ssl"):
        try:
            context = ssl.create_default_context()
            server = smtplib.SMTP_SSL(host, port, context=context)
        except ssl.SSLError:
            print("[!] SSL connection failed!")
            # If SSL was explicitely requested, fail on error
            if args.ssl == "ssl":
                raise

    # SSL failed, but we can still try to connect without SSL
    if not server:
        server = smtplib.SMTP(host, port)
        if args.ssl in ("auto", "starttls"):
            try:
                server.starttls()
            except:
                print("[!] STARTTLS failed")
                # If STARTTLS was explicitely requested, fail on error
                if args.ssl == "starttls":
                    raise

    server.login(args.username, password)
    send_emails(server, emails, args.outbox, args.sent)


def send_emails(server, emails, outbox_dir, sent_dir):
    # Create sent folder if necessary
    if not os.path.exists(sent_dir):
        os.mkdir(sent_dir)

    for eml in emails:
        msg = email.message_from_file(open(os.path.join(outbox_dir, eml)))
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
            shutil.move(os.path.join(outbox_dir, eml), os.path.join(sent_dir, eml))
        except:
            print("[!] Error when sending email to %s" % (msg["To"]))


if __name__ == "__main__":
    main()
