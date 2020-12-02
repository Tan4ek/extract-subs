from iso639 import languages as iso639

_DETECTED_TO_ISO_639_PART1_DICT = {
    "zh-cn": "zh",
    "zh-tw": "zh"
}


def convert_detect_to_iso639(lang_cde):
    """
    it's needed because langdetect package could return 'zh-cn', 'zh-tw' which are not iso-639 part1
    :param lang_cde: language code returned by from langdetect.detect
    :return: simplified iso-639 part1 code
    """
    return _DETECTED_TO_ISO_639_PART1_DICT.get(lang_cde, lang_cde)


def bcp47_language_code_to_iso_639(bcp47_code: str, default=None) -> str:
    # https://tools.ietf.org/html/bcp47#page-7
    if bcp47_code:
        return bcp47_code.split('-')[0].lower()
    else:
        return default


def iso639_from_str(lang_str: str) -> iso639:
    def _try_iso639_from_str(**kwargs) -> iso639:
        try:
            return iso639.get(**kwargs)
        except:
            return None

    if not lang_str:
        return None

    if len(lang_str) == 2:
        return _try_iso639_from_str(part1=lang_str)

    if len(lang_str) == 3:
        iso639_lang = _try_iso639_from_str(part3=lang_str)
        if not iso639_lang:
            iso639_lang = _try_iso639_from_str(part2b=lang_str)
        if not iso639_lang:
            iso639_lang = _try_iso639_from_str(part2t=lang_str)
        if not iso639_lang:
            iso639_lang = _try_iso639_from_str(part5=lang_str)
        return iso639_lang
