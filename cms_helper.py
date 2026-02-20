#!/usr/bin/env python

from tempfile import mkdtemp


def gettext(s):
    return s  # NOQA


HELPER_SETTINGS = dict(
    NOSE_ARGS=[
        "-s",
    ],
    ROOT_URLCONF="tests.test_utils.urls",
    INSTALLED_APPS=[
        "easy_thumbnails",
        "filer",
        "meta",
        "tests.test_utils",
    ],
    LANGUAGE_CODE="en",
    LANGUAGES=(
        ("en", gettext("English")),
        ("fr-fr", gettext("French")),
        ("it", gettext("Italiano")),
    ),
    CMS_LANGUAGES={
        1: [
            {
                "code": "en",
                "name": gettext("English"),
                "public": True,
            },
            {
                "code": "it",
                "name": gettext("Italiano"),
                "public": True,
            },
            {
                "code": "fr-fr",
                "name": gettext("French"),
                "public": True,
            },
        ],
        "default": {
            "hide_untranslated": False,
        },
    },
    CMS_TEMPLATES=(("page_meta.html", "page"),),
    CMS_CONFIRM_VERSION4=True,
    META_SITE_PROTOCOL="http",
    META_SITE_DOMAIN="example.com",
    META_USE_OG_PROPERTIES=True,
    META_USE_TWITTER_PROPERTIES=True,
    META_USE_SCHEMAORG_PROPERTIES=True,
    THUMBNAIL_PROCESSORS=(
        "easy_thumbnails.processors.colorspace",
        "easy_thumbnails.processors.autocrop",
        "filer.thumbnail_processors.scale_and_crop_with_subject_location",
        "easy_thumbnails.processors.filters",
    ),
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    FILE_UPLOAD_TEMP_DIR=mkdtemp(),
)


def _patch_app_helper_compat() -> None:
    """Compatibility layer for django-app-helper against django CMS 5."""
    from cms.models import Page
    from cms.utils import conf as cms_conf

    if not hasattr(Page, "publish"):

        def publish(self, language=None):
            return self

        Page.publish = publish

    if not hasattr(Page, "get_public_object"):

        def get_public_object(self):
            return self

        Page.get_public_object = get_public_object

    if not hasattr(Page, "get_draft_object"):

        def get_draft_object(self):
            return self

        Page.get_draft_object = get_draft_object

    if not hasattr(Page, "get_title_obj") and hasattr(Page, "get_content_obj"):

        def get_title_obj(self, language=None, fallback=True):
            return self.get_content_obj(language=language, fallback=fallback)

        Page.get_title_obj = get_title_obj

    original_get_cms_setting = cms_conf.get_cms_setting

    def compat_get_cms_setting(name):
        if name.startswith("CMS_"):
            name = name[4:]
        return original_get_cms_setting(name)

    cms_conf.get_cms_setting = compat_get_cms_setting

    try:
        import app_helper.base_test as app_helper_base_test

        app_helper_base_test.get_cms_setting = compat_get_cms_setting
    except Exception:
        pass


def run():
    from app_helper import runner

    runner.cms("djangocms_page_meta")


def setup():
    import sys

    from app_helper import runner

    runner.setup("djangocms_page_meta", sys.modules[__name__], use_cms=True)
    _patch_app_helper_compat()


if __name__ == "__main__":
    run()

if __name__ == "cms_helper":
    # this is needed to run cms_helper in pycharm
    setup()
