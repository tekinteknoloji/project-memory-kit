"""Preview and explicitly approve a journaled session archive."""
import argparse
import hashlib
from pathlib import Path
import re

from memory_storage import MemoryStore

ACTIVE = 'memory/SESSIONS.md'
ARCHIVE = 'memory/ARCHIVE/SESSIONS.md'
ENTRY = re.compile(rb'(?m)^- \d{4}-\d{2}-\d{2}(?: |T)')


def preview(active, archive, keep):
    starts = [match.start() for match in ENTRY.finditer(active)]
    count = max(0, len(starts) - keep)
    if not count:
        return 0, {}, ''
    start, end = starts[0], starts[count]
    changes = {
        ACTIVE: active[:start] + active[end:],
        ARCHIVE: archive.rstrip(b'\r\n') + b'\n\n' + active[start:end],
    }
    token = hashlib.sha256(
        hashlib.sha256(active).digest()
        + hashlib.sha256(archive).digest()
        + str(keep).encode()
    ).hexdigest()
    return count, changes, token


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--keep', type=int, default=80)
    parser.add_argument('--apply', metavar='PREVIEW_SHA256')
    args = parser.parse_args()
    if args.keep < 1:
        parser.error('--keep must be positive')
    store = MemoryStore(args.root)
    try:
        if args.apply is None:
            before = {name: store.path(name).read_bytes() for name in (ACTIVE, ARCHIVE)}
            count, changes, token = preview(before[ACTIVE], before[ARCHIVE], args.keep)
            print(f'{count} session records -> {ARCHIVE}')
            if count:
                first = ENTRY.search(before[ACTIVE]).start()
                end = first + len(before[ACTIVE]) - len(changes[ACTIVE])
                print(before[ACTIVE][first:end].decode('utf-8'))
                print(f'--apply {token}')
        else:
            with store.lock():
                before = store.snapshot((ACTIVE, ARCHIVE))
                count, changes, token = preview(before[ACTIVE], before[ARCHIVE], args.keep)
                if not count or args.apply != token:
                    raise ValueError('Preview is stale or empty. Run preview again.')
                store.commit(changes, before)
            print(f'{count} session records archived')
    except (ValueError, RuntimeError, OSError) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
