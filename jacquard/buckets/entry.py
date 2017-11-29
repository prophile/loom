"""Supporting classes to represent single keys within buckets."""

import collections

from jacquard.constraints import Constraints

# TODO: De-underscore these

_Entry = collections.namedtuple(
    '_Entry',
    ('key', 'settings', 'constraints'),
)


def _decode_entry(json):
    key, settings, constraints = json
    return _Entry(
        key=key,
        settings=settings,
        constraints=Constraints.from_json(constraints),
    )


def _encode_entry(entry):
    return [
        entry.key,
        entry.settings,
        entry.constraints.to_json(),
    ]
