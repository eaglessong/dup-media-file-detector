"""Usage: python3 -m dup_media ROOT [--extensions jpg,png,...]."""
import argparse
import re
import sys
import sqlite3
from .scan import DEFAULT_EXTENSIONS, Scan


def extensions(value):
    values = value.lower().split(',')
    if not values or any(not re.fullmatch(r'[a-z0-9]+', item) for item in values):
        raise argparse.ArgumentTypeError('use comma-separated extensions without dots')
    return frozenset(values)


def main():
    parser = argparse.ArgumentParser(description='Read-only exact media duplicate inventory; JSON to stdout. Store output outside ROOT.')
    parser.add_argument('root')
    parser.add_argument('--extensions', type=extensions, default=DEFAULT_EXTENSIONS)
    args = parser.parse_args()
    try:
        with Scan(args.root, args.extensions) as scan:
            scan.run()
            return scan.write(sys.stdout)
    except KeyboardInterrupt:
        print('Scan cancelled; discard any partial output.', file=sys.stderr)
        return 130
    except BrokenPipeError:
        return 1
    except (OSError, ValueError, sqlite3.Error):
        print('Scan failed: root unavailable, unsafe scratch location, or I/O failure.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
