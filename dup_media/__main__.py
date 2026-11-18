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
    parser = argparse.ArgumentParser(description='Exact media duplicate inventory, explicit relocation and completed-move restoration; JSON to stdout. Store output outside operation roots.')
    parser.add_argument('root')
    parser.add_argument('--extensions', type=extensions)
    parser.add_argument('--move-duplicates', action='store_true', help='Explicitly relocate exact duplicate paths; Linux strict metadata or macOS APFS data-only policy.')
    parser.add_argument('--revert-move', action='store_true', help='Restore a completed recorded move from ROOT; matching original subfolders must already exist.')
    parser.add_argument('--original-root', help='Legacy recovery only: original root matching the old journal.')
    parser.add_argument('--move-journal', help='Legacy recovery only: existing external move operation directory.')
    parser.add_argument('--operation', help='Recovery operation ID when the archive contains multiple operations.')
    parser.add_argument('--destination', help='Separate destination root, outside the source tree.')
    parser.add_argument('--dry-run', action='store_true', help='Plan relocation without changing either tree.')
    parser.add_argument('--journal', help='New operation directory outside both trees; parent must exist.')
    parser.add_argument('--exclusive-access', action='store_true', help='Acknowledge exclusive control of both trees and ancestors during execution.')
    args = parser.parse_args()
    if args.revert_move:
        if (args.move_duplicates or args.destination or args.journal or args.extensions is not None
                or bool(args.original_root) != bool(args.move_journal)
                or (not args.dry_run and not args.exclusive_access)):
            parser.error('revert requires either --dry-run or --exclusive-access; legacy requires both --original-root and --move-journal; forward options are not valid')
    elif args.original_root or args.move_journal or args.operation:
        parser.error('recovery-only options require --revert-move')
    elif args.move_duplicates:
        if not args.destination or (args.dry_run and args.journal) or (not args.dry_run and (not args.journal or not args.exclusive_access)):
            parser.error('relocation requires --destination and either --dry-run or --journal plus --exclusive-access')
    elif args.destination or args.dry_run or args.journal or args.exclusive_access:
        parser.error('move-only options require --move-duplicates')
    try:
        if args.revert_move:
            from .revert import Revert
            return Revert(args.root, args.original_root, args.move_journal, args.operation).run(sys.stdout, args.dry_run)
        if args.move_duplicates:
            from .relocate import Relocation
            return Relocation(args.root, args.destination, args.journal).run(args.extensions or DEFAULT_EXTENSIONS, sys.stdout, args.dry_run)
        with Scan(args.root, args.extensions or DEFAULT_EXTENSIONS) as scan:
            scan.run()
            return scan.write(sys.stdout)
    except KeyboardInterrupt:
        print('Relocation cancelled; inspect recovery records manually.' if args.move_duplicates or args.revert_move else 'Scan cancelled; discard any partial output.', file=sys.stderr)
        return 130
    except BrokenPipeError:
        return 1
    except (OSError, ValueError, sqlite3.Error):
        print(('Operation failed' if args.move_duplicates or args.revert_move else 'Scan failed')
              + ': root unavailable, unsafe scratch location, or I/O failure.', file=sys.stderr)
        return 2


if __name__ == '__main__':
    sys.exit(main())
