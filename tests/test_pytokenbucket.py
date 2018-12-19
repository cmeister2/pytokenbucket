#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Tests for `pytokenbucket` package."""

from __future__ import division
import time
import pytokenbucket
import multiprocessing.dummy as mp


def ensure_gap(timestamps, gap_ms):
    if len(timestamps) < 2:
        return

    for ii in range(len(timestamps) - 1):
        measured_gap_ms = (timestamps[ii + 1] - timestamps[ii]) * 1000

        print("Comparing: {0} - {1} = {2} ms vs {3} ms"
              .format(timestamps[ii], timestamps[ii + 1], measured_gap_ms, gap_ms))

        # Ensure that we're not drastically under the gap (can be a few ms under).
        assert measured_gap_ms >= gap_ms - 3


def test_get_tokens():
    # Create a TokenBucket that refreshes one token per second.
    one_per_second = pytokenbucket.TokenBucket(bucket_size=1,
                                               refresh_amount=1,
                                               refresh_period_ms=1000,
                                               start_filled=False)

    # Get all the tokens.
    timestamps = []

    for _i in range(2):
        token = one_per_second.get_token()

        # Ensure the token was actually gotten.
        assert token

        # Add the timestamp for this token.
        timestamps.append(time.time())

    # Ensure that the timestamps are at least 1000ms apart.
    ensure_gap(timestamps, 1000)

    one_per_second.stop()


def test_many_threads_handle_them():
    refresh_period_ms = 250

    # Create a threading pool with 5 threads.
    pool = mp.Pool(5)

    # This is the target of the apply_async method for the pool. Just returns the time it's being processed.
    def thread_target(result_number):
        return time.time()

    # Create an empty TokenBucket that refreshes one token every `refresh_period_ms`.
    one_per_second = pytokenbucket.TokenBucket(bucket_size=1,
                                               refresh_amount=1,
                                               refresh_period_ms=refresh_period_ms,
                                               start_filled=False)

    # In multiple threads, try and get results.
    results = [pool.apply_async(one_per_second.deferred_call(thread_target), args=(ii, )) for ii in range(10)]

    # Get the set of timestamps.
    timestamps = [res.get() for res in results]

    # The timestamps might be out of order, so sort them.
    timestamps.sort()

    # Ensure that the timestamps are at least `refresh_period_ms` ms apart.
    ensure_gap(timestamps, refresh_period_ms)

    one_per_second.stop()
