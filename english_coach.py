import re


# ============================================================
# RONTOGEN ENGLISH COACH
# ============================================================

PAST_TIME_PHRASES = [
    "yesterday",
    "last night",
    "last week",
    "last month",
    "last year",
    "two days ago",
    "three days ago",
    "a week ago",
    "a month ago",
    "an hour ago",
    "hours ago",
    "days ago",
    "weeks ago",
    "months ago",
    "years ago",
]


# ============================================================
# CHECK FOR PAST TIME
# ============================================================

def has_past_time(text):

    lower_text = text.lower()

    for phrase in PAST_TIME_PHRASES:

        if phrase in lower_text:
            return True

    return False


# ============================================================
# CAPITALIZATION
# ============================================================

def fix_capital_i(text):

    return re.sub(
        r"\bi\b",
        "I",
        text
    )


# ============================================================
# PAST TENSE
# ============================================================

def fix_past_tense(text):

    # Only apply these rules when there is
    # a strong past-time indicator.
    if not has_past_time(text):
        return text

    corrected = text

    # --------------------------------------------------------
    # Common irregular verbs
    # --------------------------------------------------------

    replacements = {

        r"\bgo\b": "went",
        r"\bcome\b": "came",
        r"\bsee\b": "saw",
        r"\beat\b": "ate",
        r"\bmeet\b": "met",
        r"\btake\b": "took",
        r"\bmake\b": "made",
        r"\bhave\b": "had",
        r"\bget\b": "got",
        r"\bdo\b": "did",

    }

    # We don't want to blindly replace every occurrence
    # because that could change nouns or unrelated words.
    #
    # So only apply these after common subject words.

    subjects = r"(I|he|she|we|they)"

    for verb, past in replacements.items():

        pattern = (
            rf"\b{subjects}\s+{verb[2:-2]}\b"
        )

        corrected = re.sub(
            pattern,
            lambda match: (
                match.group(1)
                + " "
                + past
            ),
            corrected,
            flags=re.IGNORECASE
        )


    # --------------------------------------------------------
    # Handle verbs after "and"
    #
    # Example:
    #
    # I go to college and meet my friend.
    #
    # becomes:
    #
    # I went to college and met my friend.
    # --------------------------------------------------------

    verb_pairs = {

        r"\bgo\b": "went",
        r"\bcome\b": "came",
        r"\bsee\b": "saw",
        r"\beat\b": "ate",
        r"\bmeet\b": "met",
        r"\btake\b": "took",
        r"\bmake\b": "made",
        r"\bhave\b": "had",
        r"\bget\b": "got",
        r"\bdo\b": "did",

    }

    for present, past in verb_pairs.items():

        pattern = (
            rf"\band\s+{present}"
        )

        corrected = re.sub(
            pattern,
            f"and {past}",
            corrected,
            flags=re.IGNORECASE
        )


    # --------------------------------------------------------
    # "I am" → "I was"
    # --------------------------------------------------------

    corrected = re.sub(
        r"\bI\s+am\b",
        "I was",
        corrected,
        flags=re.IGNORECASE
    )


    # --------------------------------------------------------
    # He / She forms
    # --------------------------------------------------------

    corrected = re.sub(
        r"\b(he|she)\s+go\b",
        r"\1 went",
        corrected,
        flags=re.IGNORECASE
    )

    corrected = re.sub(
        r"\b(he|she)\s+come\b",
        r"\1 came",
        corrected,
        flags=re.IGNORECASE
    )

    corrected = re.sub(
        r"\b(he|she)\s+meet\b",
        r"\1 met",
        corrected,
        flags=re.IGNORECASE
    )

    corrected = re.sub(
        r"\b(he|she)\s+see\b",
        r"\1 saw",
        corrected,
        flags=re.IGNORECASE
    )

    corrected = re.sub(
        r"\b(he|she)\s+eat\b",
        r"\1 ate",
        corrected,
        flags=re.IGNORECASE
    )


    return corrected


# ============================================================
# IS / ARE
# ============================================================

def fix_is_are(text):

    corrected = text

    replacements = [

        (r"\bI\s+is\b", "I am"),
        (r"\bwe\s+is\b", "we are"),
        (r"\bthey\s+is\b", "they are"),
        (r"\byou\s+is\b", "you are"),
        (r"\bhe\s+are\b", "he is"),
        (r"\bshe\s+are\b", "she is"),
        (r"\bit\s+are\b", "it is"),

    ]

    for pattern, replacement in replacements:

        corrected = re.sub(
            pattern,
            replacement,
            corrected,
            flags=re.IGNORECASE
        )

    return corrected


# ============================================================
# HAS / HAVE
# ============================================================

def fix_has_have(text):

    corrected = text

    replacements = [

        (r"\bhe\s+have\b", "he has"),
        (r"\bshe\s+have\b", "she has"),
        (r"\bit\s+have\b", "it has"),

        (r"\bthey\s+has\b", "they have"),
        (r"\bwe\s+has\b", "we have"),
        (r"\byou\s+has\b", "you have"),

    ]

    for pattern, replacement in replacements:

        corrected = re.sub(
            pattern,
            replacement,
            corrected,
            flags=re.IGNORECASE
        )

    return corrected


# ============================================================
# DO / DOES
# ============================================================

def fix_do_does(text):

    corrected = text

    replacements = [

        (r"\bhe\s+do\b", "he does"),
        (r"\bshe\s+do\b", "she does"),
        (r"\bit\s+do\b", "it does"),

        (r"\bthey\s+does\b", "they do"),
        (r"\bwe\s+does\b", "we do"),
        (r"\byou\s+does\b", "you do"),

    ]

    for pattern, replacement in replacements:

        corrected = re.sub(
            pattern,
            replacement,
            corrected,
            flags=re.IGNORECASE
        )

    return corrected


# ============================================================
# MAIN ENGLISH COACH
# ============================================================

def get_correction(text):

    if not text or not text.strip():
        return None


    # Don't attempt grammar correction on huge messages.
    if len(text.split()) > 60:
        return None


    original = text.strip()

    corrected = original


    # --------------------------------------------------------
    # IMPORTANT:
    #
    # We apply capitalization internally,
    # but capitalization ALONE will NOT trigger
    # an English correction.
    # --------------------------------------------------------

    corrected = fix_capital_i(
        corrected
    )


    # --------------------------------------------------------
    # Grammar corrections
    # --------------------------------------------------------

    corrected = fix_past_tense(
        corrected
    )

    corrected = fix_is_are(
        corrected
    )

    corrected = fix_has_have(
        corrected
    )

    corrected = fix_do_does(
        corrected
    )


    # --------------------------------------------------------
    # Capitalize first character only if we already
    # found an actual grammar correction.
    # --------------------------------------------------------

    grammar_changed = (
        corrected.lower() != original.lower()
    )


    if not grammar_changed:

        return None


    # --------------------------------------------------------
    # Correct first letter
    # --------------------------------------------------------

    if corrected:

        corrected = (
            corrected[0].upper()
            + corrected[1:]
        )


    # --------------------------------------------------------
    # Clean spaces
    # --------------------------------------------------------

    corrected = re.sub(
        r"[ \t]+",
        " ",
        corrected
    ).strip()


    return corrected


# ============================================================
# BUILD CORRECTION MESSAGE
# ============================================================

def build_correction_message(
    original,
    corrected
):

    return (
        f"Small correction: {corrected}"
    )