#!/usr/bin/env python3

import argparse
import base64
import csv
import datetime
import email.message
import email.utils
import json
import mimetypes
import pathlib
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

csv.field_size_limit(10 * 1024 * 1024)  # 10 MB


def create_attachment(main_msg: email.message.Message, file_path: pathlib.Path):
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

    msg.add_header('Content-Disposition', 'attachment', filename=file_path.name)
    main_msg.attach(msg)


def embed_image(main_msg: email.message.Message, image_path: pathlib.Path, cid: int):
    content_type, _ = mimetypes.guess_type(image_path)

    if content_type is None:
        content_type = 'application/octet-stream'

    main_type = content_type.split('/')[0]

    if main_type != 'image':
        print(f"Error: the {image_path} file does not seem to be an image.")
        return

    with image_path.open('rb') as fp:
        msg = MIMEImage(fp.read())

        msg.add_header('Content-Disposition', 'attachment', filename=image_path.name)
        msg.add_header('X-Attachment-Id', f'{cid}')
        msg.add_header('Content-ID', f'<{cid}>')

        main_msg.attach(msg)


# This is necessary because otherwise the entire From header will be encoded
# with =?...?= and that seems to break some SMTP servers.
def render_from(name, email):
    if len(name) == 0:
        return email

    if name.isascii():
        return f"{name} <{email}>"

    return f"=?utf-8?b?{base64.b64encode(name.encode()).decode()}?= <{email}>"


def generate_emails(template: str, contacts: list[dict], outbox: pathlib.Path):
    if len(contacts) == 0:
        print("No contacts found!")
        sys.exit(1)

    match = re.match(YAML_FRONT_MATTER, template, re.MULTILINE + re.DOTALL)
    if not match:
        print("The \"YAML front matter\" in the template is missing or badly formatted!")
        sys.exit(1)

    # Create the outbox folder if necessary
    if not outbox.exists():
        outbox.mkdir()

    # jinja2 with builtin support (e.g. zip, len, max, ...)
    env = jinja2.Environment(loader=jinja2.BaseLoader)
    env.globals.update(__builtins__)
    # allow json.loads inside a template
    env.globals.update(json=json)

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

        msg["From"] = render_from(*email.utils.parseaddr(config["from"]))

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

        if "list-unsubscribe" in config:
            msg["List-Unsubscribe"] = config["list-unsubscribe"]

        msg["Subject"] = config["subject"]
        msg["Date"] = email.utils.formatdate()
        msg["Message-Id"] = config["msgid"] % (str(int(datetime.datetime.timestamp(datetime.datetime.now()))) + str(random.random()))

        if "extra-headers" in config:
            for (key, value) in config["extra-headers"].items():
                msg[key] = value

        msg_alt = MIMEMultipart("alternative")
        msg_alt.attach(MIMEText(text, "plain"))
        msg_alt.attach(MIMEText(html, "html"))

        msg.attach(msg_alt)

        # Attach files
        for f in config.get("attach", []):
            create_attachment(msg, pathlib.Path(f))

        # Embed images
        for image in config.get("images", []):
            embed_image(msg, pathlib.Path(image["path"]), image["cid"])

        # Write the .eml file
        eml_filename = msg["To"].split("@")[0] + "-"
        eml_filename += "".join(filter(lambda c: '0' <= c <= '9', msg["Message-Id"]))
        eml_filename += ".eml"

        eml_path = outbox / eml_filename
        with eml_path.open("w") as outfile:
            gen = Generator(outfile)
            gen.flatten(msg)

        count += 1

        # Print progress information
        print("\r%4d / %4d" % (count, len(contacts)), end="", flush=True)

    # The cursor is still at the middle of the line
    print()
    print("Created %d mails in '%s', ready to be sent" % (count, outbox))


def main():
    parser = argparse.ArgumentParser(description="Generate emails to bulk send later.")
    parser.add_argument("template", help="a Markdown formatted document with a YAML front-matter", type=pathlib.Path)
    parser.add_argument("contacts", help="a CSV file with the contacts whom to send emails to", type=pathlib.Path)
    parser.add_argument("outbox", nargs="?", default=pathlib.Path("./outbox"), help="a folder where to save the emails (default: outbox)", type=pathlib.Path)
    args = parser.parse_args()

    if not args.template.is_file() or args.template.suffix.lower() != ".md":
        print("The template file should be a Markdown file!")
        sys.exit(1)

    if not args.contacts.is_file() or args.contacts.suffix.lower() != ".csv":
        print("The contacts file should be a CSV file!")
        sys.exit(1)

    if args.outbox.exists() and (not args.outbox.is_dir() or len(list(args.outbox.iterdir())) > 0):
        print("The outbox folder should be an empty folder, or not exist at all!")
        sys.exit(1)

    # Read template file
    with args.template.open("r", encoding='utf-8-sig') as mdfile:
        template = mdfile.read()

    # Read contacts file
    with args.contacts.open("r", encoding='utf-8-sig') as csvfile:
        contacts = list(csv.DictReader(csvfile))

    generate_emails(template, contacts, args.outbox)


if __name__ == "__main__":
    main()
