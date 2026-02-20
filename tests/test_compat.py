from django.test import SimpleTestCase

from djangocms_page_meta.compat import get_page_title_obj


class CompatTest(SimpleTestCase):
    def test_get_page_title_obj_prefers_get_content_obj(self):
        class DummyPage:
            def get_content_obj(self, language, fallback=True):
                return (language, fallback)

        self.assertEqual(get_page_title_obj(DummyPage(), "en"), ("en", True))

    def test_get_page_title_obj_falls_back_to_get_title_obj(self):
        class DummyPage:
            def get_title_obj(self, language):
                return language

        self.assertEqual(get_page_title_obj(DummyPage(), "it"), "it")
