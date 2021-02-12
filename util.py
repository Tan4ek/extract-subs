import os

import srt
from iso639 import languages as iso639
from langdetect import detect

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


def detect_iso639(lang_str: str, file_path: str) -> iso639:
    iso639_by_lang_str = iso639_from_str(lang_str)
    (_, ext) = os.path.splitext(file_path)
    lang_code_is_valid = iso639_by_lang_str is not None and iso639_by_lang_str.name != 'Undetermined'
    if not lang_code_is_valid and ext == '.srt':
        try:
            with open(file_path, 'r') as srt_file:
                srt_file_content = srt_file.read()
            srt_content = '\n'.join([x.content for x in srt.parse(srt_file_content)])
            detected_code = convert_detect_to_iso639(detect(srt_content))
            return iso639_from_str(detected_code)
        except:
            # TODO log error
            return iso639_by_lang_str
    else:
        return iso639_by_lang_str


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
