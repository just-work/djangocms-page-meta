from app_helper.base_test import BaseTestCase
from django.core.cache import cache


class DummyTokens(list):
    def __init__(self, *tokens):
        super().__init__(["dummy_tag"] + list(tokens))

    def split_contents(self):
        return self


class BaseTest(BaseTestCase):
    """
    Base class with utility function
    """

    page_data = {}
    _pages_data = (
        {
            "en": {"title": "page one", "template": "page_meta.html", "publish": False},
            "fr-fr": {"title": "page un", "publish": False},
            "it": {"title": "pagina uno", "publish": False},
        },
        {
            "en": {"title": "page two", "template": "page_meta.html", "publish": False},
            "fr-fr": {"title": "page deux", "publish": False},
            "it": {"title": "pagina due", "publish": False},
        },
    )
    title_data = {
        "keywords": "keyword1, keyword2, keyword3",
        "description": "base lorem ipsum - english",
        "og_description": "opengraph - lorem ipsum - english",
        "twitter_description": "twitter - lorem ipsum - english",
        "schemaorg_description": "gplus - lorem ipsum - english",
    }
    title_data_it = {
        "keywords": "parola1, parola2, parola3",
        "description": "base lorem ipsum - italian",
        "og_description": "opengraph - lorem ipsum - italian",
        "twitter_description": "twitter - lorem ipsum - italian",
        "schemaorg_description": "gplus - lorem ipsum - italian",
    }
    og_data = {
        "og_type": "article",
        "og_author_url": "https://facebook.com/FakeUser",
        "og_author_fbid": "123456789",
        "og_publisher": "https://facebook.com/FakeUser",
        "og_app_id": "123456789",
        "fb_pages": "PAGES123456789",
    }
    twitter_data = {
        "twitter_author": "fake_user",
        "twitter_site": "fake_site",
        "twitter_type": "summary",
    }
    robots_data_single = {"robots": "['noindex']"}
    robots_data_multiple = {"robots": "['none', 'noimageindex', 'noarchive']"}

    @staticmethod
    def get_title_obj(page, language, fallback=False):
        if hasattr(page, "get_content_obj"):
            return page.get_content_obj(language=language, fallback=fallback)
        try:
            return page.get_title_obj(language, fallback=fallback)
        except TypeError:
            return page.get_title_obj(language)

    @staticmethod
    def publish_page(page, language):
        if hasattr(page, "publish"):
            return page.publish(language)
        return page

    @staticmethod
    def get_public_page(page):
        if hasattr(page, "get_public_object"):
            return page.get_public_object()
        return page

    @staticmethod
    def get_draft_page(page):
        if hasattr(page, "get_draft_object"):
            return page.get_draft_object()
        return page

    def setUp(self):
        super().setUp()
        cache.clear()
