# This Source Code Form is subject to the terms of the GNU General Public
# License, version 3. If a copy of the GPL was not distributed with this file,
# You can obtain one at https://www.gnu.org/licenses/gpl.txt.
import logging
import socket
import sys

from contextlib import contextmanager
from threading import Thread

from rainbow_logging_handler import RainbowLoggingHandler


def enable_logging(filename: str, level: str):
    #formatter = logging.Formatter('%(pathname)s [%(module)s] - %(funcName)s:L%(lineno)d : %(message)s')
    formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s:%(message)s')

    # File logger captures everything.
    file_handler = logging.FileHandler(filename)
    file_handler.setLevel(logging.DEBUG)

    # Console output level is configurable.
    stream_handler = RainbowLoggingHandler(
        sys.stdout,
        color_asctime=('cyan', None, False),
        color_levelname=('gray', None, False),
        color_module=('yellow', None, False),
        color_name=('blue', None, False),
        color_lineno=('green', None, False),
    )
    stream_handler.setLevel(getattr(logging, level))

    # Set an output format.
    stream_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    # Add handlers to root.
    root = logging.getLogger('')
    root.setLevel(logging.DEBUG)
    root.addHandler(stream_handler)
    root.addHandler(file_handler)


def get_own_internal_ip_slow() -> str:
    """
    Discovering the active internal interface that new connections will get spawned on -- e.g. that local peers can
    (in typical networks) call back on -- is actually quite hard. We spawn a connection to an external resource and
    derive the internal network from that. A rather inelegant hack, but it gets the job done.
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))
        return s.getsockname()[0]
    except socket.error:
        return None
    finally:
        # Don't wait around for the GC.
        s.close()
        del s


class ExitableThread(Thread):
    """
    A thread that defines an exit routine.
    """
    def exit(self):
        raise NotImplementedError("This method must be overridden.")


@contextmanager
def run_thread(thread: ExitableThread):
    thread.start()
    yield thread
    thread.exit()
    thread.join()

