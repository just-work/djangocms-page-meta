from django.template.loader import render_to_string
from django.utils.safestring import mark_safe
from django.utils.translation import get_language_from_request
from meta import settings as meta_settings

from .compat import get_page_title_obj


def get_cache_key(page, language):
    """
    Create the cache key for the current page and language
    """
    from cms.cache import _get_cache_key

    try:
        site_id = page.node.site_id
    except AttributeError:  # CMS_3_4
        site_id = page.site_id
    return _get_cache_key("page_meta", page, language, site_id)


def get_page_meta(page, language):
    """
    Retrieves all the meta information for the page in the given language

    :param page: a Page instance
    :param lang: a language code

    :return: Meta instance
    :type: object
    """
    from django.core.cache import cache
    from meta.views import Meta

    from .models import DefaultMetaImage, PageMeta, TitleMeta

    try:
        meta_key = get_cache_key(page, language)
    except AttributeError:
        return None
    meta = cache.get(meta_key)
    if not meta:
        meta = Meta()
        title = get_page_title_obj(page, language)
        default_meta_image_obj = DefaultMetaImage.objects.first()
        default_meta_image = default_meta_image_obj.image if default_meta_image_obj else None
        publication_date = getattr(page, "publication_date", None)
        publication_end_date = getattr(page, "publication_end_date", None)
        changed_date = getattr(page, "changed_date", None)
        meta.extra_custom_props = []

        meta.title = page.get_page_title(language)
        if not meta.title:
            meta.title = page.get_title(language)

        if title.meta_description:
            meta.description = title.meta_description.strip()
        try:
            titlemeta = getattr(title, "titlemeta", None)
            if titlemeta is None:
                titlemeta = (
                    TitleMeta.objects.filter(extended_object__page=page, extended_object__language=language)
                    .order_by("-pk")
                    .first()
                )
            if titlemeta is None:
                raise TitleMeta.DoesNotExist
            if titlemeta.description:
                meta.description = titlemeta.description.strip()
            if titlemeta.keywords:
                meta.keywords = titlemeta.keywords.strip().split(",")
            meta.locale = titlemeta.locale
            meta.og_description = titlemeta.og_description.strip()
            if not meta.og_description:
                meta.og_description = meta.description
            meta.twitter_description = titlemeta.twitter_description.strip()
            if not meta.twitter_description:
                meta.twitter_description = meta.description
            if titlemeta.image:
                meta.image = titlemeta.image.canonical_url or titlemeta.image.url
            meta.schemaorg_description = titlemeta.schemaorg_description.strip()
            if not meta.schemaorg_description:
                meta.schemaorg_description = meta.description
            meta.schemaorg_name = titlemeta.schemaorg_name
            if not meta.schemaorg_name:
                meta.schemaorg_name = meta.title
            for item in titlemeta.extra.all():
                attribute = item.attribute
                if not attribute:
                    attribute = item.DEFAULT_ATTRIBUTE
                meta.extra_custom_props.append((attribute, item.name, item.value))
        except (TitleMeta.DoesNotExist, AttributeError):
            # Skipping title-level metas
            if meta.description:
                meta.og_description = meta.description
                meta.schemaorg_description = meta.description
                meta.twitter_description = meta.description
        defaults = {
            "object_type": meta_settings.get_setting("FB_TYPE"),
            "og_type": meta_settings.get_setting("FB_TYPE"),
            "og_app_id": meta_settings.get_setting("FB_APPID"),
            "fb_pages": meta_settings.get_setting("FB_PAGES"),
            "og_profile_id": meta_settings.get_setting("FB_PROFILE_ID"),
            "og_publisher": meta_settings.get_setting("FB_PUBLISHER"),
            "og_author_url": meta_settings.get_setting("FB_AUTHOR_URL"),
            "twitter_type": meta_settings.get_setting("TWITTER_TYPE"),
            "twitter_site": meta_settings.get_setting("TWITTER_SITE"),
            "twitter_author": meta_settings.get_setting("TWITTER_AUTHOR"),
            "schemaorg_type": meta_settings.get_setting("SCHEMAORG_TYPE"),
            "schemaorg_datePublished": publication_date.isoformat() if publication_date else None,
            "schemaorg_dateModified": changed_date.isoformat() if changed_date else None,
        }
        try:
            pagemeta = page.pagemeta
            meta.object_type = pagemeta.og_type
            meta.og_type = pagemeta.og_type
            meta.og_app_id = pagemeta.og_app_id
            meta.fb_pages = pagemeta.fb_pages
            meta.og_profile_id = pagemeta.og_author_fbid
            meta.twitter_type = pagemeta.twitter_type
            meta.twitter_site = pagemeta.twitter_site
            meta.twitter_author = pagemeta.twitter_author
            meta.schemaorg_type = pagemeta.schemaorg_type
            meta.robots = pagemeta.robots_list
            if publication_date:
                meta.published_time = publication_date.isoformat()
            if changed_date:
                meta.modified_time = changed_date.isoformat()
            if publication_end_date:
                meta.expiration_time = publication_end_date.isoformat()
            if meta.og_type == "article":
                meta.og_publisher = pagemeta.og_publisher
                meta.og_author_url = pagemeta.og_author_url
                try:
                    from djangocms_page_tags.utils import get_page_tags, get_title_tags

                    tags = list(get_title_tags(page, language))
                    tags += list(get_page_tags(page))
                    meta.tag = ",".join([tag.name for tag in tags])
                except ImportError:
                    # djangocms-page-tags not available
                    pass
            if not meta.image and pagemeta.image:
                meta.image = pagemeta.image.canonical_url or pagemeta.image.url
            for item in pagemeta.extra.all():
                attribute = item.attribute
                if not attribute:
                    attribute = item.DEFAULT_ATTRIBUTE
                meta.extra_custom_props.append((attribute, item.name, item.value))
        except PageMeta.DoesNotExist:
            pass
        for attr, val in defaults.items():
            if not getattr(meta, attr, "") and val:
                setattr(meta, attr, val)
        if not meta.image and default_meta_image:
            meta.image = default_meta_image.canonical_url or default_meta_image.url
        meta.url = page.get_absolute_url(language)
        meta.schemaorg_url = meta.url
        meta.schemaorg_image = meta.image
        cache.set(meta_key, meta)
    return meta


def get_metatags(request):
    language = get_language_from_request(request, check_path=True)
    meta = get_page_meta(request.current_page, language)
    return mark_safe(
        render_to_string(request=request, template_name="djangocms_page_meta/meta.html", context={"meta": meta})
    )
