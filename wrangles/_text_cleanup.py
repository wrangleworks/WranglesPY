"""Conservative conversions for escaped text embedded in Markdown."""

import re


_PROTECTED = re.compile(
    r"(?P<fenced>^(?: {0,3}> ?)* {0,3}(?P<fence>`{3,}|~{3,})[^\n]*(?:\n|\Z))"
    r"|(?P<indented>^(?: {4}|\t)[^\n]*(?:\n|\Z))"
    r"|(?P<reference>^ {0,3}\[[^\]\r\n]+\]:[^\r\n]*)"
    r"|(?P<code>(?<!\\)`+)"
    r"|(?P<destination>(?<!\\)\]\()"
    r"|(?P<autolink><[A-Za-z][A-Za-z0-9+.-]*:[^<>\r\n]*>)"
    r"|(?P<url>https?://[^\s<>]+)"
    r"|(?P<display_math>(?<!\\)\$\$)",
    re.MULTILINE,
)
_INLINE_MATH = r"(?<![\\$])\$(?!\$)(?=[^$\r\n]*\\)(?P<math>(?:\\[^\r\n]|[^\\$\r\n])+)\$(?!\$)"
_UNICODE_ESCAPE = (
    r"(?<!\\)\\(?:u[dD][89aAbB][0-9a-fA-F]{2}\\u[dD][c-fC-F][0-9a-fA-F]{2}"
    r"|u[0-9a-fA-F]{4}|U[0-9a-fA-F]{8})"
)
_INLINE = re.compile(_INLINE_MATH + "|(?P<unicode>" + _UNICODE_ESCAPE + ")")
_MATH_SYMBOLS = {
    "le": "≤", "leq": "≤", "ge": "≥", "geq": "≥",
    "times": "×", "cdot": "·", "pm": "±", "mu": "µ", "Omega": "Ω",
    "$": "$", "%": "%", "+": "+", "-": "-",
    ",": " ", ";": " ", ":": " ", " ": " ",
}
_DOLLAR_AMOUNT = r"\$[+-]?(?:(?:[0-9]{1,3}(?:,[0-9]{3})+|[0-9]+)(?:\.[0-9]+)?|\.[0-9]+)(?: *USD)?"
_DOLLAR_CURRENCY = re.compile(
    _DOLLAR_AMOUNT
    + r"(?: *(?:[-–—]|to) *" + _DOLLAR_AMOUNT + r")?"
    + r"(?: +(?:each|per|million|billion)\b[^$]*|/[^$]+)?",
    re.IGNORECASE,
)


def _link_end(text, start):
    """Find the end of a destination, including nested or escaped parentheses."""
    depth, quote, angle = 1, None, False
    pos = start
    while pos < len(text):
        char = text[pos]
        if char == "\\":
            pos += 2
            continue
        if angle:
            angle = char != ">"
        elif quote:
            if char == quote:
                quote = None
        elif char == "<":
            angle = True
        elif char in "\"'" and pos > start and text[pos - 1].isspace():
            quote = char
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0:
                return pos + 1
        pos += 1
    return None


def map_markdown_prose(text, transform):
    """Transform prose while retaining code, link destinations and display math."""
    parts, pos = [], 0
    while match := _PROTECTED.search(text, pos):
        start, end = match.span()
        if match.group("fenced"):
            fence = match.group("fence")
            closing = re.compile(
                r"^(?: {0,3}> ?)* {0,3}" + re.escape(fence[0])
                + "{" + str(len(fence)) + r",}[ \t]*\r?$", re.MULTILINE
            ).search(text, end)
            end = closing.end() if closing else len(text)
        elif match.group("code"):
            closing = re.compile(
                r"(?<!`)" + re.escape(match.group()) + r"(?!`)"
            ).search(text, end)
            if closing:
                end = closing.end()
        elif match.group("destination"):
            # Keep ]( with the label so a prose transform can recognize links.
            start = end
            # An unterminated destination is ambiguous; leave its tail alone.
            end = _link_end(text, end) or len(text)
        elif match.group("display_math"):
            closing = re.compile(r"(?<!\\)\$\$").search(text, end)
            end = closing.end() if closing else len(text)
        parts.append(transform(text[pos:start]))
        parts.append(text[start:end])
        pos = end
    parts.append(transform(text[pos:]))
    return "".join(parts)


def _latex_to_text(match):
    original = match.group()
    value = match.group("math")
    value = re.sub(r"\^(?:\{\\circ\}|\\circ(?![A-Za-z]))", "°", value)
    value = re.sub(
        r"\\([A-Za-z]+|[$%+\-,;: ])",
        lambda symbol: _MATH_SYMBOLS.get(symbol[1], symbol[0]),
        value,
    )
    value = re.sub(r"\\(?:text|mathrm)\{([^{}\\]*)\}", r"\1", value)
    # This is deliberately not a general TeX parser. Never partly rewrite a
    # formula containing unsupported commands, groups, powers or subscripts.
    if re.search(r"[\\{}^_]", value):
        return original
    value = re.sub(r"[ \t]+", " ", value).strip()
    # Protect complete numeric dollar amounts and their price qualifiers. Other
    # escaped dollars inside supported inline math are markup noise, regardless
    # of the unit names. Ordinary prices outside inline math never reach here.
    return value if _DOLLAR_CURRENCY.fullmatch(value) else value.replace("$", "")


def clean_escaped_text(text, *, unescape_unicode=False, latex_to_text=False):
    """Decode printable Unicode escapes and/or simple inline LaTeX notation."""
    def replace(match):
        if match.group("math") is not None:
            return _latex_to_text(match) if latex_to_text else match.group()
        if unescape_unicode:
            escaped = match.group()
            if len(escaped) == 12:  # A valid UTF-16 surrogate pair.
                high, low = int(escaped[2:6], 16), int(escaped[8:12], 16)
                codepoint = 0x10000 + ((high - 0xD800) << 10) + low - 0xDC00
            else:
                codepoint = int(escaped[2:], 16)
            if codepoint <= 0x10FFFF and chr(codepoint).isprintable():
                return chr(codepoint)
        return match.group()

    return map_markdown_prose(text, lambda prose: _INLINE.sub(replace, prose))
