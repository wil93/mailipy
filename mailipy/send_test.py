import pathlib
import time

from mailipy.send import send_emails
from mailipy.gen import generate_emails


class MockServer:
    _count = 0

    def send_message(self, _):
        self._count += 1

    def sent_count(self):
        return self._count


def get_n_emails(outbox_path: pathlib.Path, n: int) -> list[pathlib.Path]:
    template = """---

from:     "test <test@example.com>"
to:       []
cc:       []
bcc:      []
subject:  ""
msgid:    "<%s@example.com>"

---
"""

    generate_emails(template, [dict() for _ in range(n)], outbox_path)
    return list(outbox_path.iterdir())


def test_sleep_after_send(tmp_path):
    outbox_path = (tmp_path / 'outbox')
    outbox_path.mkdir()
    sent_path = (tmp_path / 'sent')
    sent_path.mkdir()

    emails = get_n_emails(outbox_path, 2)

    start_time = time.time()
    send_emails(MockServer(), emails, sent_path, 1)

    elapsed_time = time.time() - start_time
    assert 1.9 < elapsed_time < 2.1


def test_send_message_is_called(tmp_path):
    outbox_path = (tmp_path / 'outbox')
    outbox_path.mkdir()
    sent_path = (tmp_path / 'sent')
    sent_path.mkdir()

    emails = get_n_emails(outbox_path, 2)

    server = MockServer()
    send_emails(server, emails, sent_path, 0)

    assert server.sent_count() == 2
