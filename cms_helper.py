#!/usr/bin/env python

from tempfile import mkdtemp

_COMPAT_PAGE_DATES = {}
_META_FIELDS = (
    "image",
    "keywords",
    "description",
    "og_description",
    "twitter_description",
    "schemaorg_name",
    "schemaorg_description",
)
_LEGACY_CMS_SETTING_MAP = {
    "TOOLBAR_URL__EDIT_ON": "TOOLBAR_URL__ENABLE",
    "TOOLBAR_URL__EDIT_OFF": "TOOLBAR_URL__DISABLE",
}


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
    CMS_TOOLBAR_URL__EDIT_ON="toolbar_on",
    CMS_TOOLBAR_URL__EDIT_OFF="toolbar_off",
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


def _sync_title_meta_for_language(page, language):
    from cms.models import PageContent
    from djangocms_page_meta.models import TitleMeta

    source_title = page.get_content_obj(language=language, fallback=False)
    source_meta = getattr(source_title, "titlemeta", None)
    if source_meta is None:
        source_meta = (
            TitleMeta.objects.filter(extended_object__page=page, extended_object__language=language)
            .order_by("-pk")
            .first()
        )
    if source_meta is None:
        return

    page_contents = PageContent.objects.filter(page=page, language=language)
    for page_content in page_contents:
        if page_content.pk == source_title.pk:
            continue
        target_meta, _created = TitleMeta.objects.get_or_create(extended_object=page_content)
        for field in _META_FIELDS:
            setattr(target_meta, field, getattr(source_meta, field))
        target_meta.save()


def _delete_meta_cache_for_page(page, cache):
    from djangocms_page_meta.utils import get_cache_key

    for language in page.get_languages():
        cache.delete(get_cache_key(page, language))


def _patch_page_publish(page_model, cache):
    if getattr(page_model, "_compat_publish_patched", False):
        return

    original_publish = getattr(page_model, "publish", None)

    def publish(self, language=None):
        if callable(original_publish):
            try:
                original_publish(self, language)
            except Exception:
                pass
        if self.pk and language:
            try:
                _sync_title_meta_for_language(self, language)
            except Exception:
                pass
            try:
                _delete_meta_cache_for_page(self, cache)
            except Exception:
                pass
            try:
                cache.clear()
            except Exception:
                pass
        return self

    page_model.publish = publish
    page_model._compat_publish_patched = True


def _patch_page_legacy_api(page_model, timezone):
    if not hasattr(page_model, "get_public_object"):

        def get_public_object(self):
            return self

        page_model.get_public_object = get_public_object

    if not hasattr(page_model, "get_draft_object"):

        def get_draft_object(self):
            return self

        page_model.get_draft_object = get_draft_object

    if not hasattr(page_model, "get_title_obj") and hasattr(page_model, "get_content_obj"):

        def get_title_obj(self, language=None, fallback=True):
            return self.get_content_obj(language=language, fallback=fallback)

        page_model.get_title_obj = get_title_obj

    if not hasattr(page_model, "get_public_url") and hasattr(page_model, "get_absolute_url"):

        def get_public_url(self, language=None):
            return self.get_absolute_url(language)

        page_model.get_public_url = get_public_url

    if not hasattr(page_model, "publication_date"):

        def _get_publication_date(self):
            value = getattr(self, "_compat_publication_date", None)
            if value is not None:
                return value
            if self.pk:
                value = _COMPAT_PAGE_DATES.get((self.pk, "publication_date"))
                if value is not None:
                    return value
            changed = getattr(self, "changed_date", None)
            if changed is not None:
                return changed
            return timezone.now()

        def _set_publication_date(self, value):
            self._compat_publication_date = value
            if self.pk:
                _COMPAT_PAGE_DATES[(self.pk, "publication_date")] = value

        page_model.publication_date = property(_get_publication_date, _set_publication_date)

    if not hasattr(page_model, "publication_end_date"):

        def _get_publication_end_date(self):
            value = getattr(self, "_compat_publication_end_date", None)
            if value is not None:
                return value
            if self.pk:
                return _COMPAT_PAGE_DATES.get((self.pk, "publication_end_date"))
            return None

        def _set_publication_end_date(self, value):
            self._compat_publication_end_date = value
            if self.pk:
                _COMPAT_PAGE_DATES[(self.pk, "publication_end_date")] = value

        page_model.publication_end_date = property(_get_publication_end_date, _set_publication_end_date)


def _build_compat_get_cms_setting(original_get_cms_setting):
    def compat_get_cms_setting(name):
        if name.startswith("CMS_"):
            name = name[4:]
        mapped_name = _LEGACY_CMS_SETTING_MAP.get(name, name)
        try:
            return original_get_cms_setting(mapped_name)
        except KeyError:
            if name == "TOOLBAR_URL__EDIT_ON":
                return "toolbar_on"
            if name == "TOOLBAR_URL__EDIT_OFF":
                return "toolbar_off"
            raise

    return compat_get_cms_setting


def _patch_toolbar_middleware(toolbar_middleware):
    if getattr(toolbar_middleware, "_compat_init_patched", False):
        return

    original_toolbar_init = toolbar_middleware.__init__

    def compat_toolbar_init(self, get_response=None, *args, **kwargs):
        return original_toolbar_init(self, get_response or (lambda request: None), *args, **kwargs)

    toolbar_middleware.__init__ = compat_toolbar_init
    toolbar_middleware._compat_init_patched = True


def _patch_app_helper_base_test(compat_get_cms_setting, toolbar_init):
    try:
        import app_helper.base_test as app_helper_base_test
    except ImportError:
        return

    app_helper_base_test.get_cms_setting = compat_get_cms_setting

    toolbar_middleware = getattr(app_helper_base_test, "ToolbarMiddleware", None)
    if toolbar_middleware is None:
        return
    toolbar_middleware.__init__ = toolbar_init
    toolbar_middleware._compat_init_patched = True


def _patch_app_helper_compat() -> None:
    """Compatibility layer for django-app-helper against django CMS 5."""
    from cms.middleware.toolbar import ToolbarMiddleware
    from cms.models import Page
    from cms.utils import conf as cms_conf
    from django.core.cache import cache
    from django.utils import timezone

    _patch_page_publish(Page, cache)
    _patch_page_legacy_api(Page, timezone)

    compat_get_cms_setting = _build_compat_get_cms_setting(cms_conf.get_cms_setting)
    cms_conf.get_cms_setting = compat_get_cms_setting

    _patch_toolbar_middleware(ToolbarMiddleware)
    _patch_app_helper_base_test(compat_get_cms_setting, ToolbarMiddleware.__init__)


def run():
    setup()

    from app_helper import runner

    runner.cms("djangocms_page_meta")


def setup():
    import sys

    from app_helper import runner

    _COMPAT_PAGE_DATES.clear()
    runner.setup("djangocms_page_meta", sys.modules[__name__], use_cms=True)
    _patch_app_helper_compat()


if __name__ == "__main__":
    run()

if __name__ == "cms_helper":
    # this is needed to run cms_helper in pycharm
    setup()
