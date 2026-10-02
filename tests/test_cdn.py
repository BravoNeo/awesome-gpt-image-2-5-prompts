import copy, unittest, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from catalog import load_entries, validate_entries

class CdnIntegrityTests(unittest.TestCase):
    def test_hosted_catalog_validates(self):
        self.assertTrue(load_entries())
    def test_hosted_bytes_cannot_be_rebound_to_a_different_hash(self):
        entries = copy.deepcopy(load_entries())
        first = entries[0]
        cdn = first['media'][0]['cdn'] if 'media' in first else first['video']['cdn']
        cdn['sha256'] = '0' * 64
        with self.assertRaises(ValueError): validate_entries(entries)
    def test_zero_width_is_rejected(self):
        entries = copy.deepcopy(load_entries())
        first = entries[0]
        cdn = first['media'][0]['cdn'] if 'media' in first else first['video']['posterCdn']
        cdn['width'] = 0
        with self.assertRaises(ValueError): validate_entries(entries)
