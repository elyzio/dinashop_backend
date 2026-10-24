from django.conf import settings
from django.utils import translation


def _configured_language_from_header(header: str) -> str | None:
    supported = {code.lower(): code for code, _label in settings.LANGUAGES}
    preferences: list[tuple[float, int, str]] = []

    for position, item in enumerate(header.split(",")):
        parts = [part.strip() for part in item.split(";")]
        language = parts[0].lower().replace("_", "-")
        quality = 1.0

        for parameter in parts[1:]:
            if not parameter.startswith("q="):
                continue
            try:
                quality = float(parameter[2:])
            except ValueError:
                quality = 0.0

        if language and quality > 0:
            preferences.append((quality, -position, language))

    for _quality, _position, language in sorted(preferences, reverse=True):
        if language == "*":
            return settings.LANGUAGE_CODE
        if language in supported:
            return supported[language]
        base_language = language.split("-", 1)[0]
        if base_language in supported:
            return supported[base_language]

    return None


class ConfiguredLanguageMiddleware:
    """Activate explicitly configured API languages before catalogs exist."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        language = _configured_language_from_header(
            request.headers.get("Accept-Language", "")
        )
        if language is not None:
            translation.activate(language)
            request.LANGUAGE_CODE = language

        return self.get_response(request)
