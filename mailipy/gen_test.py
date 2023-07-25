import email
import os
import shutil

from mailipy.gen import generate_emails

def test_create_two_emails(tmp_path):
    shutil.copy('logo.png', os.path.join(tmp_path, 'logo.png'));
    shutil.copy('logo.png', os.path.join(tmp_path, 'test.png'));
    
    os.chdir(tmp_path)

    outbox = 'outbox'

    template = """---

from:     "🇮🇹 Test 🏆 <admin@example.com>"
to:       ["{{email}}"]
cc:       ["cc@example.com"]
bcc:      ["bcc@example.com"]
reply-to: "info@example.com"
subject:  "Invitation for {{name}}"
msgid:    "<%s@example.com>"
attach:
  - "test.png"
images:
  - path: "./logo.png"
    cid: 0

---

![](cid:0)

Test email for {{name}}.
"""

    contacts = [
        {'email': 'test@example.com', 'name': 'Mr. Test'},
        {'email': 'test-2@example.com', 'name': 'Mr. Test 2'},
    ]

    generate_emails(template, contacts, outbox)

    assert len(os.listdir(outbox)) == 2

    for file_name in os.listdir(outbox):
        msg = email.message_from_file(open(os.path.join(outbox, file_name)))

        email_without_domain = msg['To'].split('@')[0]
        assert file_name.startswith(email_without_domain)
        assert msg.is_multipart()
        assert 'cc@example.com' in msg['cc']
        assert 'bcc@example.com' in msg['bcc']
        assert 'info@example.com' in msg['reply-to']

        multipart, attachment, embedded_image = msg.get_payload()
        plaintext, html = multipart.get_payload()

        # TODO: improve how we test for email content
        assert 'Test email for Mr. Test' in plaintext.as_string()
        assert '<p>Test email for Mr. Test' in html.as_string()
        assert 'Content-Disposition: attachment; filename="test.png"' in attachment.as_string()
        assert 'Content-Disposition: attachment; filename="logo.png"' in embedded_image.as_string()
