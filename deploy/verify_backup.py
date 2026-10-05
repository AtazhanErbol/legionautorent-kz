"""Read-only preflight for local JSON manifests and Compose SHA256 backups."""
import argparse
import hashlib
import json
import re
import tarfile
from pathlib import Path, PurePosixPath


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def verify_backup(dump, media, manifest=None):
    dump, media = Path(dump), Path(media)
    for path in (dump, media):
        if not path.is_file() or path.is_symlink():
            raise ValueError('Backup must be an existing regular file: ' + str(path))
    match = re.fullmatch(r'legion-(\d{8}T\d{6}Z)\.dump', dump.name)
    if not match or media.name != f'media-{match[1]}.tar.gz':
        raise ValueError('Database and media must have the same backup timestamp.')
    if manifest is None:
        candidates = [dump.parent / f'{prefix}-{match[1]}.{suffix}'
                      for prefix, suffix in [('manifest', 'json'), ('checksums', 'txt')]]
        manifest = next((path for path in candidates if path.is_file()), None)
        if manifest is None:
            raise ValueError('Matching manifest/checksums is missing; copy it with the backup.')
    manifest = Path(manifest)
    if manifest.suffix == '.json':
        values = json.loads(manifest.read_text(encoding='utf-8'))
        if not isinstance(values, dict):
            raise ValueError('JSON manifest must be an object.')
        if values.get('database') != dump.name or values.get('media') != media.name:
            raise ValueError('Manifest filenames do not match this backup pair.')
        checksums = {dump.name: values.get('database_sha256', ''),
                     media.name: values.get('media_sha256', '')}
    else:
        checksums = {}
        for line in manifest.read_text(encoding='utf-8').splitlines():
            if not line.strip():
                continue
            entry = re.fullmatch(r'([a-fA-F0-9]{64}) [ *](.+)', line)
            if not entry:
                raise ValueError('Invalid SHA256 checksum entry.')
            name = PurePosixPath(entry[2]).name
            if name in checksums:
                raise ValueError('Duplicate checksum filename: ' + name)
            checksums[name] = entry[1]
    for path in (dump, media):
        expected = checksums.get(path.name, '')
        if not isinstance(expected, str) or not re.fullmatch(r'[a-fA-F0-9]{64}', expected):
            raise ValueError('Missing or invalid checksum: ' + path.name)
        if sha256(path) != expected.lower():
            raise ValueError('SHA256 mismatch: ' + path.name)
    with dump.open('rb') as source:
        if source.read(5) != b'PGDMP':
            raise ValueError('Database backup must use PostgreSQL custom format.')
    files = 0
    seen = set()
    with tarfile.open(media, 'r:gz') as archive:
        for member in archive:
            path = PurePosixPath(member.name)
            if (not path.parts or path.is_absolute() or '..' in path.parts
                    or '\\' in member.name or ':' in member.name
                    or path.parts[0] != 'media'
                    or not (member.isfile() or member.isdir())
                    or (len(path.parts) == 1 and not member.isdir())
                    or path.as_posix() in seen):
                raise ValueError('Unsafe or duplicate archive member: ' + member.name)
            seen.add(path.as_posix())
            files += int(member.isfile())
    if not files:
        raise ValueError('Media archive contains no files.')
    return {'manifest': str(manifest), 'database': dump.name,
            'media': media.name, 'media_files': files, 'verified': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dump', type=Path)
    parser.add_argument('media', type=Path)
    parser.add_argument('--manifest', type=Path)
    args = parser.parse_args()
    try:
        result = verify_backup(args.dump, args.media, args.manifest)
    except (OSError, ValueError, tarfile.TarError, EOFError) as error:
        parser.exit(1, f'Backup verification failed: {error}\n')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
