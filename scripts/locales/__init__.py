from scripts.locales.en import TEXTS as EN_TEXTS
from scripts.locales.zh import TEXTS as ZH_TEXTS
from scripts.add_documents import SUPPORTED_DOCUMENT_EXTENSIONS_TEXT


DEFAULT_LANG = "zh"
LANGUAGE_CHOICES = [("简体中文", "zh"), ("English", "en")]

LANG = {
    "zh": ZH_TEXTS,
    "en": EN_TEXTS,
}


def normalize_lang(lang):
    return lang if lang in LANG else DEFAULT_LANG


def t(key, lang=None, **kwargs):
    lang = normalize_lang(lang or DEFAULT_LANG)
    text = LANG[lang].get(key, LANG[DEFAULT_LANG].get(key, key))
    format_values = {"supported_extensions": SUPPORTED_DOCUMENT_EXTENSIONS_TEXT}
    format_values.update(kwargs)
    try:
        text = text.format(**format_values)
    except KeyError:
        pass
    return text
