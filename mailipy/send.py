#!/usr/bin/env python3

import argparse
import email
import getpass
import pathlib
import shutil
import smtplib
import ssl
import sys
import time

from importlib.metadata import version


def read_password_from_file(file_path):
    with open(file_path) as f:
        return f.readline().strip()


def send_emails(server: smtplib.SMTP_SSL, emails: list[pathlib.Path], sent_dir: pathlib.Path, sleep_after_send: int):
    # Create sent folder if necessary
    if not sent_dir.exists():
        sent_dir.mkdir()

    for eml in emails:
        msg = email.message_from_file(eml.open())
        try:
            extra = []
            if "Cc" in msg:
                extra += ["cc: " + msg["Cc"]]
            if "Bcc" in msg:
                extra += ["bcc: " + msg["Bcc"]]
            if extra:
                extra = " (%s)" % " | ".join(extra)
            else:
                extra = ""
            print("Sending email to %s%s..." % (msg["To"], extra))
            server.send_message(msg)

            # On success, move the message from the outbox to the sent folder
            shutil.move(eml, sent_dir / eml.name)
        except Exception:
            print("[!] Error when sending email to %s" % (msg["To"]))

        if sleep_after_send > 0:
            time.sleep(sleep_after_send)


def main():
    parser = argparse.ArgumentParser(description="Bulk send emails from the 'outbox' folder.")
    parser.add_argument("server", help="the URL of the SMTP server, including the port")
    parser.add_argument("username", help="the username to login to the mail server")
    parser.add_argument("outbox", help="the folder where to access the emails that should be sent", type=pathlib.Path)
    parser.add_argument("sent", nargs="?", default=pathlib.Path("./sent"), help="the folder where to move the emails sent (default: sent)", type=pathlib.Path)
    parser.add_argument("--continue", help="continue sending, even if the 'sent' folder is not empty", action="store_true", dest="continue_")
    parser.add_argument("--password-file", help="path to a file containing the password to login to the mail server")
    parser.add_argument("--ssl", help="SSL mode to use", choices=["auto", "none", "starttls", "ssl"], default="auto")
    parser.add_argument("--sleep", help="seconds to wait after each sent email", type=int, default=0)
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version="mailipy {v}".format(v=version("mailipy")),
    )
    args = parser.parse_args()

    if not args.outbox.is_dir() or len(list(args.outbox.iterdir())) == 0:
        print("The outbox folder should contain some emails!")
        sys.exit(1)

    # FIXME: skip the check if --continue was specified... but actually we should still check that: 'sent' is a directory AND it doesn't contain files which also exist in 'outbox'
    if not args.continue_:
        if args.sent.exists() and (not args.sent.is_dir() or len(list(args.sent.iterdir())) > 0):
            print("The sent folder should be an empty folder, or not exist at all!")
            sys.exit(1)

    password = None
    if args.password_file:
        password = read_password_from_file(args.password_file)

    host, port = args.server.split(":")
    port = int(port)

    emails = list(args.outbox.iterdir())

    if any(not eml_path.is_file() or eml_path.suffix.lower() != ".eml" for eml_path in emails):
        print("The outbox folder contains invalid files!")
        sys.exit(1)

    print("You are about to send %d emails." % len(emails))
    if password is None:
        password = getpass.getpass("Password for %s@%s: " % (args.username, args.server))
    else:
        getpass.getpass("Press [Enter] to confirm: ")

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
            except Exception:
                print("[!] STARTTLS failed")
                # If STARTTLS was explicitely requested, fail on error
                if args.ssl == "starttls":
                    raise

    server.login(args.username, password)
    send_emails(server, emails, args.sent, args.sleep)


if __name__ == "__main__":
    main()
