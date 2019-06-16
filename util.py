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
