"""Useful commands for Jacquard development."""

import io
import json
import itertools
import contextlib

from werkzeug.test import Client

from jacquard.cli import main as run_command
from jacquard.service import get_wsgi_app
from jacquard.commands import BaseCommand, CommandError
from jacquard.utils_dev import shrink
from jacquard.storage.dummy import DummyStore
from jacquard.storage.utils import copy_data


class Bugpoint(BaseCommand):
    """
    Minimise error by reducing storage.

    Drops keys from storage to minimise the size of test case needed to
    reproduce an exception.
    """

    help = "minimise test case from storage"

    plumbing = True

    def add_arguments(self, parser):
        """Add command-line arguments."""
        target = parser.add_mutually_exclusive_group(required=True)

        target.add_argument(
            '--command',
            type=str,
            help="command to run",
            nargs='*',
        )
        target.add_argument(
            '--url',
            type=str,
            help="url to fetch",
        )

    def handle(self, config, options):
        """Run command."""
        log = print

        if options.command:
            def target():
                out_stream = io.StringIO()

                with contextlib.ExitStack() as context:
                    context.enter_context(
                        contextlib.redirect_stdout(out_stream),
                    )
                    context.enter_context(
                        contextlib.redirect_stderr(out_stream),
                    )

                    run_command(options.command, config)
        elif options.url:
            app = get_wsgi_app(config)
            test_client = Client(app)

            def target():
                result = test_client.get(options.url)

                status_class = str(result.status_code)[0]

                if status_class in ('4', '5'):
                    raise ValueError("Class 4 or 5 status")

        def target_failure_mode():
            try:
                target()
            except KeyboardInterrupt:
                # Pass through ^C
                raise
            except Exception as exc:
                return repr(exc)
            else:
                return None

        reference_failure_mode = target_failure_mode()

        if reference_failure_mode is None:
            raise CommandError("Target is not currently failing")

        log("Taking backup of state")
        backup = DummyStore('')
        copy_data(config.storage, backup)

        # Sequence 1: Simplify by dropping keys
        pass_number = itertools.count(1)

        any_changes = True
        log("Dropping keys")
        while any_changes:
            log("Loop {}".format(next(pass_number)))
            any_changes = False

            # Get list of keys
            config.storage.begin_read_only()
            all_keys = list(config.storage.keys())
            config.storage.rollback()
            all_keys.sort()

            for key in all_keys:
                # Try dropping this key and see what happens
                config.storage.begin()
                old_value = config.storage.get(key)
                config.storage.commit({}, (key,))

                failure_mode = target_failure_mode()

                if failure_mode != reference_failure_mode:
                    # This either passes the tests or changes the failure mode,
                    # and so must be kept.
                    config.storage.begin()
                    config.storage.commit({key: old_value}, ())
                else:
                    log("Dropped key {}".format(key))
                    any_changes = True

        # Sequence 1: Simplify by dropping keys
        pass_number = itertools.count(1)

        any_changes = True
        while any_changes:
            log("Loop {}".format(next(pass_number)))
            any_changes = False

            # Get list of keys
            config.storage.begin_read_only()
            all_keys = list(config.storage.keys())
            config.storage.rollback()
            all_keys.sort()

            for key in all_keys:
                # Try dropping this key and see what happens
                config.storage.begin()
                old_value = config.storage.get(key)
                config.storage.commit({}, (key,))

                failure_mode = target_failure_mode()

                if failure_mode != reference_failure_mode:
                    # This either passes the tests or changes the failure mode,
                    # and so must be kept.
                    config.storage.begin()
                    config.storage.commit({key: old_value}, ())
                else:
                    log("Dropped key {}".format(key))
                    any_changes = True

        # Sequence 2: Progressively simplify all remaining keys
        log("Simplifying keys")
        pass_number = itertools.count(1)

        any_changes = True
        while any_changes:
            log("Loop {}".format(next(pass_number)))
            any_changes = False

            # Get list of keys
            config.storage.begin_read_only()
            all_keys = list(config.storage.keys())
            config.storage.rollback()
            all_keys.sort()

            for key in all_keys:
                # Try to shrink this key
                config.storage.begin()
                old_value = config.storage.get(key)
                config.storage.commit({}, (key,))

                def test_validity(new_json):
                    dumped_json = json.dumps(new_json)
                    config.storage.begin()
                    config.storage.commit({key: dumped_json}, ())

                    failure_mode = target_failure_mode()

                    return failure_mode == reference_failure_mode

                parsed_old_value = json.loads(old_value)

                shrunk_value = shrink(parsed_old_value, test_validity)

                config.storage.begin()
                config.storage.commit({key: json.dumps(shrunk_value)}, ())

                if shrunk_value != parsed_old_value:
                    log("Shrunk key: {}".format(key))
                    any_changes = True

        log("Done bugpointing")

        run_command(["storage-dump"], config)

        log("Restoring state from backup")
        copy_data(backup, config.storage)
