# -*- coding: utf-8 -*-
"""Implementation of a thread-safe token bucket using threads and queues."""

from __future__ import print_function, division
from six.moves import queue
import logging
import threading
import time
log = logging.getLogger(__name__)


class TokenBucket(object):
    """A token bucket. Tokens can be requested using `get_token`."""

    def __init__(self,
                 bucket_size=10,
                 refresh_amount=1,
                 refresh_period_ms=1000,
                 start_filled=True):
        """Construct a TokenBucket instance."""
        super(TokenBucket, self).__init__()

        self.bucket_size = bucket_size
        self.refresh_amount = refresh_amount
        self.refresh_period_ms = refresh_period_ms
        self.timer_queue = queue.Queue(self.bucket_size)
        self.stopper = threading.Event()

        if start_filled:
            # Fill the queue.
            for _i in range(self.bucket_size):
                self.timer_queue.put(True)

        # Create a thread which handles the filling of the queue.
        self.token_thread = threading.Thread(name="tokenbucket", target=self._token_filler)
        self.token_thread.setDaemon(True)
        self.token_thread.start()

    def _token_filler(self):
        log.debug("Starting token filler thread")
        while not self.stopper.is_set():
            added = 0
            for _i in range(self.refresh_amount):
                try:
                    self.timer_queue.put_nowait(True)
                    added += 1
                except queue.Full:
                    pass

            log.debug("Added %d/%d tokens to bucket (approx size %d), sleeping %f ms",
                      added,
                      self.refresh_amount,
                      self.timer_queue.qsize(),
                      self.refresh_period_ms)
            time.sleep(self.refresh_period_ms / 1000)

    def stop(self):
        """Stop the token bucket pending a shutdown."""
        log.debug("Stopping token filler thread")
        self.stopper.set()
        self.token_thread.join()
        log.debug("Stopped token filler thread")

    def get_token(self):
        """Get a token. Blocks until a token is retrieved or the token bucket is stopped."""
        while True:
            try:
                token = self.timer_queue.get(timeout=self.refresh_period_ms / 1000)
                self.timer_queue.task_done()
                return token
            except queue.Empty:
                # The queue is empty when there are no more tokens. Wait for more tokens.
                if self.stopper.is_set():
                    # The token bucket is stopping. Return false for this request.
                    return False

    def deferred_call(self, callable):
        """Return a callable which calls the argument when a token is available."""
        def _proxy(*args, **kwargs):
            if self.get_token():
                return callable(*args, **kwargs)

        return _proxy
