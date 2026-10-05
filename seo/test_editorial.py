import json
import tempfile
from pathlib import Path
from django.test import SimpleTestCase,override_settings
from seo.editorial import editorial_expected

class ExactEditorialTests(SimpleTestCase):
    def test_only_recorded_field_and_matching_original_receive_an_exception(self):
        with tempfile.TemporaryDirectory() as directory,override_settings(BASE_DIR=Path(directory)):
            folder=Path(directory)/'migration';folder.mkdir()
            (folder/'seo_editorial_overrides.json').write_text(json.dumps({'pages':{'/car/example':{'title':{'before':'Old title','after':'New city title'}}}}),encoding='utf8')
            self.assertEqual(editorial_expected('/car/example','title','Old title'),'New city title')
            self.assertEqual(editorial_expected('/car/example','title','Unexpected source'),'Unexpected source')
            self.assertEqual(editorial_expected('/car/other','title','Old title'),'Old title')
            self.assertEqual(editorial_expected('/car/example','h1','Old title'),'Old title')
