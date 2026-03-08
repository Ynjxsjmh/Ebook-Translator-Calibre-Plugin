import unittest

from unittest.mock import patch

from ...lib.cache import Paragraph, TranslationCache, CACHE_SCHEMA_VERSION


class TestParagraph(unittest.TestCase):
    def setUp(self):
        self.paragraph = Paragraph(
            1, 'TEST', 'a\n\nb\n\nc', 'a\n\nb\n\nc\n\n',
            translation='A\n\nB\n\nC', attributes='{"class": "test"}')

    def test_created_paragraph(self):
        self.assertIsInstance(self.paragraph, Paragraph)
        self.assertFalse(self.paragraph.is_cache)
        self.assertIsNone(self.paragraph.error)
        self.assertTrue(self.paragraph.aligned)

    def test_get_attributes(self):
        self.assertEqual({'class': 'test'}, self.paragraph.get_attributes())

    def test_check_translation(self):
        self.assertTrue(self.paragraph.is_alignment('\n\n'))

        self.paragraph.original = 'a\n\nb\n\nc'
        self.paragraph.translation = 'A\n\nB\nC\n\n'
        self.assertFalse(self.paragraph.is_alignment('\n\n'))

    def test_is_alignment(self):
        # Test with empty translation.
        self.paragraph.translation = None
        self.assertTrue(self.paragraph.is_alignment('\n\n'))

        self.paragraph.translation = ''
        self.assertTrue(self.paragraph.is_alignment('\n\n'))

        self.paragraph.translation = '   '
        self.assertTrue(self.paragraph.is_alignment('\n\n'))

        self.paragraph.original = 'a\n\nb\n\nc'
        self.paragraph.translation = 'A\n\nB\n\nC'
        self.assertTrue(self.paragraph.is_alignment('\n\n'))

        # Alignment determination ignores line breaks at the start and end.
        self.paragraph.translation = '\n\nA\n\nB\n\nC\n\n'
        self.assertTrue(self.paragraph.is_alignment('\n\n'))

        self.paragraph.original = 'a\n\nb'
        self.paragraph.translation = 'A\n\nB\n\nC'
        self.assertFalse(self.paragraph.is_alignment('\n\n'))

        self.paragraph.original = 'a\n\nb\n\nc'
        self.paragraph.translation = 'A\n\nB'
        self.assertFalse(self.paragraph.is_alignment('\n\n'))

    def test_do_alignment(self):
        # Test with empty translation
        self.paragraph.translation = None
        self.paragraph.do_aligment('\n\n')
        self.assertIsNone(self.paragraph.translation)

        self.paragraph.translation = ''
        self.paragraph.do_aligment('\n\n')
        self.assertEqual('', self.paragraph.translation)

        self.paragraph.translation = '   '
        self.paragraph.do_aligment('\n\n')
        self.assertEqual('   ', self.paragraph.translation)

        # Test with no alignment needed.
        self.paragraph.original = 'a\n\nb\n\nc'
        self.paragraph.translation = 'A\n\nB\n\nC'
        self.paragraph.do_aligment('\n')
        self.assertEqual('A\n\nB\n\nC', self.paragraph.translation)

        self.paragraph.translation = 'A\n\nB\nC'
        self.paragraph.do_aligment('\n\n')
        self.assertEqual('A\n\nB\n\nC', self.paragraph.translation)


class TestTranslationCache(unittest.TestCase):
    def test_rebuild_preserves_translation_by_original(self):
        # Use an in-memory sqlite database for isolation.
        with patch.object(TranslationCache, '_path', return_value=':memory:'):
            cache = TranslationCache('unittest', persistence=True)
            original_group = [
                (0, 'md5-0', '<p>Hello</p>', 'Hello', False, None, 'p1')
            ]

            # Initial save will set the schema version.
            cache.save(original_group)
            self.assertEqual(CACHE_SCHEMA_VERSION, cache.cache_schema_version())

            # Seed a cached translation.
            cache.update(0, translation='Hola', engine_name='Mock', target_lang='es')

            # Force a schema mismatch and ensure we rebuild without losing the
            # existing translation when the original text still matches.
            cache.set_info('cache_schema_version', '0')
            self.assertTrue(cache.needs_rebuild())
            cache.save(original_group)

            paragraph = cache.paragraph(0)
            self.assertEqual('Hello', paragraph.original)
            self.assertEqual('Hola', paragraph.translation)
