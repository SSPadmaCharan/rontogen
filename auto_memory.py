from memory_manager import remember, load_memory
import re


# ---------------------------------------------------------
# AUTOMATIC MEMORY DETECTION
# ---------------------------------------------------------

def detect_automatic_memory(text):
    """
    Detect whether a user statement contains useful information
    that Rontogen should remember.

    Returns:
        (category, prefix)
        or
        (None, None)
    """

    text = text.strip()

    if not text:
        return None, None

    lower = text.lower()

    # Ignore questions
    if "?" in text:
        return None, None

    # -----------------------------------------------------
    # PREFERENCES
    # -----------------------------------------------------

    preference_patterns = [
        "i prefer ",
        "i like ",
        "i love ",
        "i don't like ",
        "i dislike ",
        "i want you to ",
        "i would prefer ",
        "my preference is ",
        "i usually prefer "
    ]

    if any(lower.startswith(pattern) for pattern in preference_patterns):
        return "preferences", "preference"

    # -----------------------------------------------------
    # GOALS
    # -----------------------------------------------------

    goal_patterns = [
        "my goal is ",
        "my goal for ",
        "i want to finish ",
        "i want to complete ",
        "i plan to ",
        "i am planning to ",
        "i'm planning to ",
        "i hope to ",
        "i need to "
    ]

    if any(lower.startswith(pattern) for pattern in goal_patterns):
        return "goals", "goal"

    # -----------------------------------------------------
    # PERSONAL FACTS
    # -----------------------------------------------------

    fact_patterns = [
        "i am studying ",
        "i'm studying ",
        "i study ",
        "i am learning ",
        "i'm learning ",
        "i work as ",
        "i am working as ",
        "i'm working as ",
        "i live in ",
        "i am from ",
        "i'm from "
    ]

    if any(lower.startswith(pattern) for pattern in fact_patterns):
        return "facts", "fact"

    # -----------------------------------------------------
    # PROJECTS
    # -----------------------------------------------------

    project_patterns = [
        "i'm working on ",
        "i am working on ",
        "i'm building ",
        "i am building ",
        "i'm developing ",
        "i am developing ",
        "i'm making ",
        "i am making ",
        "i'm designing ",
        "i am designing "
    ]

    if any(lower.startswith(pattern) for pattern in project_patterns):
        return "projects", "project"

    # -----------------------------------------------------
    # RONTOGEN-SPECIFIC PROJECT INFORMATION
    # -----------------------------------------------------

    if "rontogen" in lower:

        rontogen_keywords = [
            "will",
            "should",
            "eventually",
            "physical",
            "device",
            "body",
            "assistant",
            "project",
            "feature",
            "system",
            "hardware"
        ]

        if any(word in lower for word in rontogen_keywords):
            return "projects", "rontogen"

    return None, None


# ---------------------------------------------------------
# KEY GENERATOR
# ---------------------------------------------------------

def create_key(category, prefix):
    """
    Creates a unique key such as:

        auto_project_1
        auto_project_2
        auto_fact_1

    It checks the existing memory so keys remain unique
    even after restarting the program.
    """

    memory = load_memory()

    section = memory.get(category, {})

    highest_number = 0

    pattern = re.compile(
        rf"^auto_{re.escape(prefix)}_(\d+)$"
    )

    for key in section.keys():

        match = pattern.match(key)

        if match:
            number = int(match.group(1))

            if number > highest_number:
                highest_number = number

    return f"auto_{prefix}_{highest_number + 1}"


# ---------------------------------------------------------
# TEXT NORMALIZATION
# ---------------------------------------------------------

def normalize_memory_text(text):
    """
    Basic normalization so small differences such as:

        Rontogen
        rontogen

    or extra spaces don't create duplicates.
    """

    text = text.lower().strip()

    # Normalize contractions
    replacements = {
        "i'm": "i am",
        "i'd": "i would",
        "i've": "i have",
        "i'll": "i will",
        "it's": "it is",
        "rontogen's": "rontogen"
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    # Remove punctuation
    text = re.sub(r"[^\w\s]", " ", text)

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text)

    return text.strip()


# ---------------------------------------------------------
# WORD GROUPS
# ---------------------------------------------------------

# Words that commonly represent the same idea.

WORD_GROUPS = [

    {
        "device",
        "physical",
        "hardware",
        "machine",
        "system"
    },

    {
        "body",
        "physical",
        "device",
        "hardware"
    },

    {
        "build",
        "building",
        "make",
        "making",
        "develop",
        "developing",
        "create",
        "creating"
    },

    {
        "want",
        "wish",
        "hope",
        "plan",
        "planning"
    },

    {
        "eventually",
        "future",
        "later"
    },

    {
        "project",
        "system"
    },

    {
        "study",
        "studying",
        "learn",
        "learning"
    }
]


# ---------------------------------------------------------
# CANONICAL WORD
# ---------------------------------------------------------

def canonical_word(word):
    """
    Converts related words into a common representative word.
    """

    for group in WORD_GROUPS:

        if word in group:

            # Pick a stable representative.
            return sorted(group)[0]

    return word


# ---------------------------------------------------------
# MEMORY SIGNATURE
# ---------------------------------------------------------

def memory_signature(text):
    """
    Converts a sentence into a simplified representation.

    Example:

    "Rontogen will eventually have a physical body"

    becomes a normalized set of meaningful concepts.
    """

    normalized = normalize_memory_text(text)

    words = normalized.split()

    # Remove very common filler words.
    stop_words = {
        "i",
        "am",
        "a",
        "an",
        "the",
        "is",
        "are",
        "was",
        "were",
        "to",
        "of",
        "for",
        "on",
        "in",
        "my",
        "me",
        "it",
        "will",
        "have",
        "has",
        "that",
        "and",
        "be",
        "this",
        "as"
    }

    meaningful_words = []

    for word in words:

        if word in stop_words:
            continue

        word = canonical_word(word)

        meaningful_words.append(word)

    return set(meaningful_words)


# ---------------------------------------------------------
# SEMANTIC DUPLICATE CHECK
# ---------------------------------------------------------

def memory_already_exists(category, value):
    """
    Checks whether the memory is already present.

    First performs an exact normalized comparison.

    Then performs a lightweight meaning-based comparison
    using memory signatures.
    """

    memory = load_memory()

    section = memory.get(category, {})

    new_normalized = normalize_memory_text(value)

    new_signature = memory_signature(value)

    if not new_signature:
        return False

    for existing_value in section.values():

        existing_text = str(existing_value)

        # ---------------------------------------------
        # EXACT NORMALIZED MATCH
        # ---------------------------------------------

        existing_normalized = normalize_memory_text(
            existing_text
        )

        if existing_normalized == new_normalized:
            return True

        # ---------------------------------------------
        # SEMANTIC-STYLE MATCH
        # ---------------------------------------------

        existing_signature = memory_signature(
            existing_text
        )

        if not existing_signature:
            continue

        intersection = (
            new_signature &
            existing_signature
        )

        union = (
            new_signature |
            existing_signature
        )

        if not union:
            continue

        similarity = len(intersection) / len(union)

        # High similarity = probably the same memory.
        if similarity >= 0.60:
            return True

    return False


# ---------------------------------------------------------
# SAVE AUTOMATIC MEMORY
# ---------------------------------------------------------

def save_automatic_memory(text):
    """
    Detect useful information and save it automatically.

    Returns:

        True  -> new memory saved
        False -> nothing saved
    """

    category, prefix = detect_automatic_memory(text)

    if category is None:
        return False

    # -----------------------------------------------------
    # DUPLICATE CHECK
    # -----------------------------------------------------

    if memory_already_exists(category, text):
        print("Automatic memory skipped: duplicate detected.")
        return False

    # -----------------------------------------------------
    # CREATE UNIQUE KEY
    # -----------------------------------------------------

    key = create_key(category, prefix)

    # -----------------------------------------------------
    # SAVE
    # -----------------------------------------------------

    remember(
        category,
        key,
        text.strip()
    )

    print(
        f"Automatic memory saved: "
        f"{category} -> {key}"
    )

    return True


# ---------------------------------------------------------
# TEST
# ---------------------------------------------------------

if __name__ == "__main__":

    print("Rontogen Automatic Memory Test")
    print("--------------------------------")

    test_statements = [

        "I'm working on a drone project.",

        "I prefer a female voice for Rontogen.",

        "My goal is to finish Rontogen this year.",

        "I am studying aerospace engineering.",

        "What is a voltage regulator?",

        "The weather is nice today.",

        "Rontogen will eventually have a physical body.",

        "I want Rontogen to eventually become a physical device."

    ]

    for statement in test_statements:

        print()
        print("Statement:", statement)

        result = save_automatic_memory(statement)

        if result:
            print("Result: SAVED")
        else:
            print("Result: NOT SAVED")

    print()
    print("Automatic memory test completed.")