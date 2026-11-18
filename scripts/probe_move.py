"""Bounded synthetic relocation measurement; no private paths or external media."""
import io
import json
from pathlib import Path
import resource
import tempfile
import time
from unittest.mock import patch

from dup_media.relocate import Relocation
from dup_media.scan import DEFAULT_EXTENSIONS


class Sink:
    def write(self, text):
        return len(text)

    def flush(self):
        pass


def main():
    with tempfile.TemporaryDirectory() as t:
        base = Path(t).resolve()
        source = base / 'source'
        source.mkdir()
        for i in range(5000):
            data = i.to_bytes(8, 'big') * 2
            for suffix in ['a', 'b']:
                (source / f'{i:05}{suffix}.jpg').write_bytes(data)
        measurements = {}
        original = Relocation.preflight
        def observe(operation, scan):
            original(operation, scan)
            measurements['index_bytes'] = Path(scan.temp.name, 'index.sqlite').stat().st_size
        start = time.monotonic()
        with patch.object(Relocation, 'preflight', observe):
            code = Relocation(source, base / 'dest').run(DEFAULT_EXTENSIONS, Sink(), True)
        assert code == 0
        measurements.update(files=10000, source_bytes=160000, phase='dry_run',
                            seconds=round(time.monotonic()-start, 3),
                            peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        print(json.dumps(measurements))
    with tempfile.TemporaryDirectory() as t:
        base = Path(t).resolve()
        source = base / 'source'
        source.mkdir()
        for name in ['a.jpg', 'b.jpg']:
            with (source / name).open('wb') as stream:
                for _ in range(16):
                    stream.write(b'x' * 1024**2)
        start = time.monotonic()
        code = Relocation(source, base / 'dest', base / 'journal').run(DEFAULT_EXTENSIONS, Sink(), False)
        assert code == 0 and not (source / 'b.jpg').exists()
        assert (base / 'dest/b.jpg').stat().st_size == 16*1024**2
        print(json.dumps(dict(phase='transfer', moved_bytes=16*1024**2,
                              seconds=round(time.monotonic()-start,3),
                              peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)))


if __name__ == '__main__':
    main()
