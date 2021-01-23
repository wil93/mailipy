#!/usr/bin/env python3

import argparse
import csv
import datetime
import email.utils
import mimetypes
import os
import random
import re
import sys
from email.generator import Generator
from email.mime.application import MIMEApplication
from email.mime.audio import MIMEAudio
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import jinja2
import markdown
import yaml


YAML_FRONT_MATTER = r"\A(---\s*\n.*?\n?)^((---|\.\.\.)\s*$\n?)(.*)"
BASE_HTML = """<!DOCTYPE html>
<html>
    <head>
        <style>
        body {{
            font-size: larger;
            font-family: sans-serif;
        }}
        </style>
    </head>
    <body>
        {body}
    </body>
</html>"""


def create_attachment(main_msg, file_path):
    content_type, _ = mimetypes.guess_type(file_path)

    if content_type is None:
        content_type = 'application/octet-stream'

    main_type = content_type.split('/')[0]

    if main_type == 'text':
        with open(file_path, 'rb') as fp:
            msg = MIMEText(fp.read())
    elif main_type == 'image':
        with open(file_path, 'rb') as fp:
            msg = MIMEImage(fp.read())
    elif main_type == 'audio':
        with open(file_path, 'rb') as fp:
            msg = MIMEAudio(fp.read())
    else:
        with open(file_path, 'rb') as fp:
            msg = MIMEApplication(fp.read())

    filename = os.path.basename(file_path)
    msg.add_header('Content-Disposition', 'attachment', filename=filename)
    main_msg.attach(msg)


def embed_image(main_msg, image_path, cid):
    content_type, _ = mimetypes.guess_type(image_path)

    if content_type is None:
        content_type = 'application/octet-stream'

    main_type = content_type.split('/')[0]

    if main_type != 'image':
        print(f"Error: the {image_path} file does not seem to be an image.")
        return

    with open(image_path, 'rb') as fp:
        msg = MIMEImage(fp.read())

        filename = os.path.basename(image_path)
        msg.add_header('Content-Disposition', 'attachment', filename=filename)
        msg.add_header('X-Attachment-Id', f'{cid}')
        msg.add_header('Content-ID', f'<{cid}>')

        main_msg.attach(msg)


def main():
    parser = argparse.ArgumentParser(description="Generate emails to bulk send later.")
    parser.add_argument("template", help="a Markdown formatted document with a YAML front-matter")
    parser.add_argument("contacts", help="a CSV file with the contacts whom to send emails to")
    parser.add_argument("outbox", nargs="?", default="outbox", help="a folder where to save the emails (default: outbox)")
    args = parser.parse_args()

    if (not os.path.isfile(args.template)) or (not args.template.lower().endswith(".md")):
        print("The template file should be a Markdown file!")
        sys.exit(1)

    if (not os.path.isfile(args.contacts)) or (not args.contacts.lower().endswith(".csv")):
        print("The contacts file should be a CSV file!")
        sys.exit(1)

    if os.path.exists(args.outbox) and ((not os.path.isdir(args.outbox)) or len(os.listdir(args.outbox)) > 0):
        print("The outbox folder should be an empty folder, or not exist at all!")
        sys.exit(1)

    # Read template file
    with open(args.template, "r") as mdfile:
        template = mdfile.read()

    # Read contacts file
    with open(args.contacts, "r") as csvfile:
        contacts = list(csv.DictReader(csvfile))

    if len(contacts) == 0:
        print("No contacts found!")
        sys.exit(1)

    match = re.match(YAML_FRONT_MATTER, template, re.MULTILINE + re.DOTALL)
    if not match:
        print("The \"YAML front matter\" in the template is missing or badly formatted!")
        sys.exit(1)

    # Create the outbox folder if necessary
    if not os.path.exists(args.outbox):
        os.mkdir(args.outbox)

    # jinja2 with builtin support (e.g. zip, len, max, ...)
    env = jinja2.Environment(loader=jinja2.BaseLoader)
    env.globals.update(__builtins__)

    def render_template(template, data):
        return env.from_string(template).render(data)

    count = 0

    for data in contacts:
        # Load config from the front matter
        config = render_template(match.group(1), data)
        config = yaml.safe_load(config)

        # Load the email text from after the front matter
        text = render_template(match.group(4), data)
        html = markdown.markdown(text, extensions=['tables'])
        html = BASE_HTML.format(body=html)

        msg = MIMEMultipart("mixed")

        msg["From"] = config["from"]

        # This is necessary to support the case where "to:" contains a single string (maybe we can drop this use-case though...)
        if not isinstance(config["to"], list):
            # Convert string to a list with one string
            config["to"] = [config["to"]]

        msg["To"] = ', '.join(filter(bool, config["to"]))

        if "cc" in config:
            msg["Cc"] = ", ".join(filter(bool, config["cc"]))

        if "bcc" in config:
            msg["Bcc"] = ", ".join(filter(bool, config["bcc"]))

        if "reply-to" in config:
            msg["Reply-To"] = config["reply-to"]

        msg["Subject"] = config["subject"]
        msg["Date"] = email.utils.formatdate()
        msg["Message-Id"] = config["msgid"] % (datetime.datetime.now().strftime("%s") + str(random.random()))

        if "extra-headers" in config:
            for (key, value) in config["extra-headers"].items():
                msg[key] = value

        msg_alt = MIMEMultipart("alternative")
        msg_alt.attach(MIMEText(text, "plain"))
        msg_alt.attach(MIMEText(html, "html"))

        msg.attach(msg_alt)

        # Attach files
        for f in config["attach"]:
            create_attachment(msg, f)

        # Embed images
        for image in config["images"]:
            embed_image(msg, image["path"], image["cid"])

        # Write the .eml file
        eml_filename = msg["To"].split("@")[0] + "-"
        eml_filename += "".join(filter(lambda c: '0' <= c <= '9', msg["Message-Id"]))
        eml_filename += ".eml"
        with open(os.path.join(args.outbox, eml_filename), "w") as outfile:
            gen = Generator(outfile)
            gen.flatten(msg)

        count += 1

    print("Created %d mails in '%s', ready to be sent" % (count, args.outbox))


if __name__ == "__main__":
    main()
