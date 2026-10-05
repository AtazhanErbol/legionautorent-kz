"""Corrupt/mismatched backups must fail before restoration is attempted."""
import io
import json
import tarfile
import tempfile
from pathlib import Path
from django.test import SimpleTestCase
from deploy.verify_backup import sha256, verify_backup


class BackupPackageTests(SimpleTestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.dump = self.root / 'legion-20261005T050000Z.dump'
        self.media = self.root / 'media-20261005T050000Z.tar.gz'
        self.manifest = self.root / 'manifest-20261005T050000Z.json'
        self.dump.write_bytes(b'PGDMPtest-fixture')
        self.archive('media/car.webp')

    def archive(self, name, kind=tarfile.REGTYPE):
        with tarfile.open(self.media, 'w:gz') as archive:
            member = tarfile.TarInfo(name)
            member.type = kind
            member.size = 4 if kind == tarfile.REGTYPE else 0
            member.linkname = '../../outside' if kind in (tarfile.SYMTYPE, tarfile.LNKTYPE) else ''
            archive.addfile(member, io.BytesIO(b'car!') if member.size else None)
        self.write_manifest()

    def write_manifest(self):
        self.manifest.write_text(json.dumps({
            'database': self.dump.name, 'media': self.media.name,
            'database_sha256': sha256(self.dump), 'media_sha256': sha256(self.media),
        }), encoding='utf-8')

    def test_local_json_manifest(self):
        self.assertEqual(verify_backup(self.dump, self.media)['media_files'], 1)

    def test_compose_checksum_format_and_explicit_manifest(self):
        checksums = self.root / 'checksums-20261005T050000Z.txt'
        checksums.write_text(''.join(f'{sha256(p)}  backups/{p.name}\n' for p in (self.dump, self.media)))
        self.assertTrue(verify_backup(self.dump, self.media, checksums)['verified'])
        self.manifest.rename(self.root / 'saved-manifest.json')
        self.assertTrue(verify_backup(self.dump, self.media)['verified'])

    def test_corrupted_dump_and_archive(self):
        for path in (self.dump, self.media):
            with self.subTest(path=path.name):
                original = path.read_bytes()
                path.write_bytes(original + b'corruption')
                with self.assertRaisesRegex(ValueError, 'SHA256 mismatch'):
                    verify_backup(self.dump, self.media)
                path.write_bytes(original)

    def test_wrong_backup_pair(self):
        other = self.media.with_name('media-20261005T060000Z.tar.gz')
        self.media.rename(other)
        with self.assertRaisesRegex(ValueError, 'same backup timestamp'):
            verify_backup(self.dump, other)

    def test_missing_manifest(self):
        self.manifest.rename(self.root / 'saved.json')
        with self.assertRaisesRegex(ValueError, 'missing'):
            verify_backup(self.dump, self.media)

    def test_manifest_must_describe_selected_files(self):
        values = json.loads(self.manifest.read_text())
        values['database'] = 'another.dump'
        self.manifest.write_text(json.dumps(values))
        with self.assertRaisesRegex(ValueError, 'filenames'):
            verify_backup(self.dump, self.media)

    def test_unsafe_members_and_links(self):
        for name, kind in [('media/../../outside', tarfile.REGTYPE),
                           ('/media/file', tarfile.REGTYPE), ('other/file', tarfile.REGTYPE),
                           ('media', tarfile.REGTYPE), ('media/link', tarfile.SYMTYPE),
                           ('media/link', tarfile.LNKTYPE), ('media/pipe', tarfile.FIFOTYPE)]:
            with self.subTest(name=name, kind=kind):
                self.archive(name, kind)
                with self.assertRaisesRegex(ValueError, 'Unsafe'):
                    verify_backup(self.dump, self.media)

    def test_empty_archive(self):
        self.archive('media', tarfile.DIRTYPE)
        with self.assertRaisesRegex(ValueError, 'no files'):
            verify_backup(self.dump, self.media)

    def test_plain_sql_is_not_a_custom_dump(self):
        self.dump.write_bytes(b'SELECT 1;')
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, 'custom format'):
            verify_backup(self.dump, self.media)
