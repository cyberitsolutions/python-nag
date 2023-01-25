#!/usr/bin/python3
"""Rewrite of nag2al in Python3."""
import datetime
import pathlib
import shlex
# import subprocess
import sys

ITEM_LENGTH_RESOLUTION = datetime.timedelta(minutes=15)
TIMELOG_FILE = pathlib.Path('~/.nag/timelog')

offset_lines = 13830  # FIXME: Save this in a file alongside timelog


def add_timesheet_item(start_time: datetime.datetime, length: datetime.timedelta, task: int, comment: str, multiplier: int = 1):
    """
    Add a timesheet line item to Alloc.

    FIXME: This should either use alloc-cli as a Python library, or do HTTP calls directly.
    """
    length -= length % ITEM_LENGTH_RESOLUTION
    cmd = ['alloc', 'work', '--quiet', '--task', str(task), '--multiplier', str(multiplier),
           '--date', start_time.strftime('%Y-%m-%d'), '--hours', str(length.total_seconds() / 3600),
           '--comment', f"{comment} [{start_time.strftime('%H:%M')}]"]
    if not length:
        # NOTE: alloc-work does this check AIUI, so maybe just rely on that.
        #       However that would mean not crashing at the first hint of trouble from alloc-cli
        #       (assuming it actually exits non-zero anyway)
        print("# ERROR: Asked to add zero-length item", file=sys.stderr)
        print('#       ', shlex.join(cmd), file=sys.stderr)
    print(shlex.join(cmd))


with TIMELOG_FILE.expanduser().resolve().open('r') as timelog:
    # Separate loops used just for simplicity's sake
    # theoretically optimizes it too by stopping the "are we there yet" checks once we are actually there
    current_line = 0  # Accumulator for skipping past offset_lines
    for line in timelog:
        current_line += 1
        if current_line >= offset_lines:
            break

    start_datetime = None
    start_taskcomment = None
    for line in timelog:
        # FIXME: Fix the timelog so that the timestamps have a 'T' instead of a ' ', then get rid of this line
        # FIXME: Alternatively, use the known-length of a timestamp instead of '.split',
        #        since any isoformat timestamp should always have the same number of characters.
        line = line.replace(' ', 'T', 1)

        line_timestamp, line_taskcomment = line.strip().split(maxsplit=1)

        if start_taskcomment != line_taskcomment:
            # New task/comment, process what we just found the length of
            line_datetime = datetime.datetime.fromisoformat(line_timestamp)
            if not (start_taskcomment is None and start_datetime is None):
                task, comment = start_taskcomment.split(maxsplit=1)
                if '*' in task:
                    task, multiplier = task.rsplit('*', 1)
                else:
                    multiplier = 1

                # Handle a few non-int edge cases:
                if not task.isdigit():
                    # * I put a task ID of "-----" as a divider for clocking off and such
                    if task == '-----':
                        print('# Divider line found, ignoring and continuing:', comment)
                    # * I put a task ID of "?????" when I don't (yet) have a task ID for certain work
                    elif task == '?????':
                        print('# ERROR: Task ID not updated', file=sys.stderr)
                        print('#      ', start_datetime, line_datetime - start_datetime, int(task), '*', int(multiplier), comment,
                              file=sys.stderr)
                else:
                    add_timesheet_item(start_time=start_datetime, length=line_datetime - start_datetime,
                                       multiplier=int(multiplier), task=int(task), comment=comment)

            start_datetime = line_datetime
            start_taskcomment = line_taskcomment
