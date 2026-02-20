def get_page_title_obj(page, language):
    """Returns title/content object for current CMS version."""
    if hasattr(page, "get_content_obj"):
        return page.get_content_obj(language=language, fallback=True)
    return page.get_title_obj(language)
