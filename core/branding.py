"""The owner's unified brand spelling, preserving URLs and code identifiers."""
import re

BRAND = 'LEGIONAUTORENT'
_OLD_BRAND = re.compile(r'(?<![\w/@.\-])(?:legion(?:[ \t]*auto(?:[ \t]*rent)?)?|легион(?:[ \t]*авто(?:[ \t]*рент)?)?|легионе|легионда)(?![\w@\-]|\.[a-z])', re.IGNORECASE)


def brand_text(value):
    return _OLD_BRAND.sub(BRAND, value or '')
