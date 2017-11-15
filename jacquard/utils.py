"""General utility functions."""


import difflib


def check_keys(passed_keys, known_keys, exception=ValueError):
    """
    Validate that all elements of passed_keys are in known_keys.

    Raises ValueError if not.

    Also makes the error message useful.
    """
    # Upfront conversion to set in case the iterable is not re-usable
    known_keys = set(known_keys)

    unknown_keys = set(passed_keys) - known_keys

    if not unknown_keys:
        return

    if len(unknown_keys) > 1:
        raise exception("Unknown keys: {keys}".format(
            keys=", ".join(sorted(unknown_keys)),
        ))

    (unknown_key,) = unknown_keys

    if len(known_keys) > 3:
        close_matches = difflib.get_close_matches(unknown_key, known_keys)
        close_matches_string = "close matches"
    else:
        close_matches = list(known_keys)
        close_matches_string = "choices"

    if not close_matches:
        raise exception("Unknown key: {key}".format(key=unknown_key))

    if len(close_matches) == 1:
        (close_match,) = close_matches
        raise exception(
            "Unknown key: {key} (did you mean {suggestion}?)".format(
                key=unknown_key,
                suggestion=close_match,
            ),
        )

    raise exception(
        "Unknown key: {key} ({suggestions_heading}: {suggestions})".format(
            key=unknown_key,
            suggestions_heading=close_matches_string,
            suggestions=", ".join(close_matches),
        ),
    )
