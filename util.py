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


def bcp47_language_code_to_iso_639(bcp47_code: str) -> str:
    # https://tools.ietf.org/html/bcp47#page-7
    if bcp47_code:
        return bcp47_code.split('-')[0]
    else:
        return bcp47_code
