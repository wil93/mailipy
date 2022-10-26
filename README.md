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

# Contributing

You can make changes to the [`gen.py`](./mailipy/gen.py) and
[`send.py`](./mailipy/send.py) scripts, and test these changes by running a
local version of Mailipy. After testing your changes, you can open a pull
request.

## Running a local version of Mailipy

1. Make sure you have [pipenv](https://pipenv.pypa.io/) installed in your
   system.
2. Run `pipenv install` followed by `pipenv shell` from the root of the source
   directory.
3. Install by running `python setup.py install` from the root of the source
   directory.
4. Now you can run `mailipy-gen` and `mailipy-send`, and these will include your
   local changes. You can verify that you're running a different binary than the
   one installed with `pip` by running `which mailipy-gen`: the command will
   return the full path of the binary you're using.
