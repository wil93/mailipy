# Mailipy

This is a software to make the task of sending bulk emails to a list of contacts
easier.

## Installation

    $ pip install mailipy

In order to send emails, you need to first **generate** them and later **send**
them.

## Generating emails

You need to prepare a `template.md` file which must have a _YAML front matter_
(similarly to [what you find in
Jekyll](https://jekyllrb.com/docs/front-matter/)). See the example for the
keywords required in the front matter.

The command to create the emails is the following:

    $ mailipy-gen template.md contacts.csv

This will create as many emails as there are records in `contacts.csv`. The
emails will be stored in `outbox/` by default. You can use a third parameter to
change the outbox destination folder.

## Sending emails

Once you created the emails, run the following command (changing the outbox
directory accordingly):

    $ mailipy-send mail.example.com:528 my_username outbox

The command will inform you of how many emails are going to be sent, and then
will prompt you for a password.
