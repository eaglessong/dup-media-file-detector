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
    parser.add_argument('--move-duplicates', action='store_true', help='Explicitly relocate exact duplicate paths; Linux capabilities required.')
    parser.add_argument('--destination', help='Separate destination root, outside the source tree.')
    parser.add_argument('--dry-run', action='store_true', help='Plan relocation without changing either tree.')
    parser.add_argument('--journal', help='New operation directory outside both trees; parent must exist.')
    parser.add_argument('--exclusive-access', action='store_true', help='Acknowledge exclusive control of both trees and ancestors during execution.')
    args = parser.parse_args()
    if args.move_duplicates:
        if not args.destination or (args.dry_run and args.journal) or (not args.dry_run and (not args.journal or not args.exclusive_access)):
            parser.error('relocation requires --destination and either --dry-run or --journal plus --exclusive-access')
    elif args.destination or args.dry_run or args.journal or args.exclusive_access:
        parser.error('move-only options require --move-duplicates')
    try:
        if args.move_duplicates:
            from .relocate import Relocation
            return Relocation(args.root, args.destination, args.journal).run(args.extensions, sys.stdout, args.dry_run)
        with Scan(args.root, args.extensions) as scan:
            scan.run()
            return scan.write(sys.stdout)
    except KeyboardInterrupt:
        print('Relocation cancelled; inspect the operation journal.' if args.move_duplicates else 'Scan cancelled; discard any partial output.', file=sys.stderr)
        return 130
    except BrokenPipeError:
        return 1
    except (OSError, ValueError, sqlite3.Error):
        print('Scan failed: root unavailable, unsafe scratch location, or I/O failure.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
