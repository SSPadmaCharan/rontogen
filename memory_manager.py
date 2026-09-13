import json
import os


# ============================================================
# RONTOGEN MEMORY MANAGER
# ============================================================

MEMORY_FILE = "memory.json"


# ============================================================
# DEFAULT MEMORY STRUCTURE
# ============================================================

DEFAULT_MEMORY = {
    "user": {},
    "preferences": {},
    "projects": {},
    "goals": {},
    "facts": {}
}


# ============================================================
# CREATE DEFAULT MEMORY
# ============================================================

def create_default_memory():

    return {
        "user": {},
        "preferences": {},
        "projects": {},
        "goals": {},
        "facts": {}
    }


# ============================================================
# LOAD MEMORY
# ============================================================

def load_memory():

    if not os.path.exists(MEMORY_FILE):

        return create_default_memory()


    try:

        with open(
            MEMORY_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            memory = json.load(file)

    except (json.JSONDecodeError, OSError):

        print("Warning: Could not read memory.json.")
        print("Starting with empty memory.")

        return create_default_memory()


    # --------------------------------------------------------
    # Make sure the root is a dictionary
    # --------------------------------------------------------

    if not isinstance(memory, dict):

        print("Warning: Invalid memory structure.")
        print("Starting with empty memory.")

        return create_default_memory()


    # --------------------------------------------------------
    # Make sure every main section exists
    # --------------------------------------------------------

    for section in DEFAULT_MEMORY:

        if section not in memory:

            memory[section] = {}

        elif not isinstance(
            memory[section],
            dict
        ):

            # Older versions may have used lists.
            # Replace invalid sections with dictionaries.
            memory[section] = {}


    return memory


# ============================================================
# SAVE MEMORY
# ============================================================

def save_memory(memory):

    try:

        with open(
            MEMORY_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                memory,
                file,
                indent=4,
                ensure_ascii=False
            )

    except OSError as error:

        print(
            f"Warning: Could not save memory: {error}"
        )


# ============================================================
# REMEMBER
# ============================================================

def remember(
    category,
    key,
    value
):

    memory = load_memory()


    # --------------------------------------------------------
    # Create category if necessary
    # --------------------------------------------------------

    if category not in memory:

        memory[category] = {}


    if not isinstance(
        memory[category],
        dict
    ):

        memory[category] = {}


    # --------------------------------------------------------
    # Store memory
    # --------------------------------------------------------

    memory[category][key] = value


    save_memory(
        memory
    )


# ============================================================
# GET ONE MEMORY
# ============================================================

def get_memory(
    category,
    key
):

    memory = load_memory()


    return memory.get(
        category,
        {}
    ).get(
        key,
        None
    )


# ============================================================
# GET CATEGORY
# ============================================================

def get_category(
    category
):

    memory = load_memory()


    return memory.get(
        category,
        {}
    )


# ============================================================
# SEARCH MEMORY
# ============================================================

def search_memory(
    query
):

    memory = load_memory()


    if not query or not query.strip():

        return []


    query_words = query.lower().split()


    results = []


    # --------------------------------------------------------
    # Search all memory categories
    # --------------------------------------------------------

    for category, items in memory.items():

        if not isinstance(
            items,
            dict
        ):

            continue


        for key, value in items.items():

            searchable_text = (

                str(category)
                + " "
                + str(key)
                + " "
                + str(value)

            ).lower()


            score = 0


            # ------------------------------------------------
            # Score matching words
            # ------------------------------------------------

            for word in query_words:

                if word in searchable_text:

                    score += 1


            if score > 0:

                results.append({

                    "category": category,

                    "key": key,

                    "value": value,

                    "score": score

                })


    # --------------------------------------------------------
    # Highest score first
    # --------------------------------------------------------

    results.sort(
        key=lambda item: item["score"],
        reverse=True
    )


    return results


# ============================================================
# BUILD MEMORY CONTEXT
# ============================================================

def build_memory_context(
    query=None
):

    # --------------------------------------------------------
    # No query
    # --------------------------------------------------------

    if not query:

        memory = load_memory()


        return json.dumps(
            memory,
            indent=2,
            ensure_ascii=False
        )


    # --------------------------------------------------------
    # Search
    # --------------------------------------------------------

    results = search_memory(
        query
    )


    if not results:

        return "{}"


    relevant_memory = {}


    # --------------------------------------------------------
    # Keep top results
    # --------------------------------------------------------

    for item in results[:8]:

        category = item["category"]

        key = item["key"]

        value = item["value"]


        if category not in relevant_memory:

            relevant_memory[category] = {}


        relevant_memory[category][key] = value


    return json.dumps(
        relevant_memory,
        indent=2,
        ensure_ascii=False
    )


# ============================================================
# BUILD CATEGORY CONTEXT
# ============================================================

def build_category_context(
    category
):

    memory = load_memory()


    items = memory.get(
        category,
        {}
    )


    if not isinstance(
        items,
        dict
    ):

        return "{}"


    return json.dumps(
        {
            category: items
        },
        indent=2,
        ensure_ascii=False
    )


# ============================================================
# DISPLAY MEMORY
# ============================================================

def show_memory():

    memory = load_memory()


    print(
        json.dumps(
            memory,
            indent=4,
            ensure_ascii=False
        )
    )


# ============================================================
# FORGET ONE MEMORY
# ============================================================

def forget(
    category,
    key
):

    memory = load_memory()


    if category not in memory:

        return False


    if key not in memory[category]:

        return False


    del memory[category][key]


    save_memory(
        memory
    )


    return True


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    print(
        "Rontogen Memory Manager Test"
    )

    print(
        "--------------------------------"
    )


    remember(
        "projects",
        "rontogen",
        "Rontogen is a personal AI assistant project."
    )


    remember(
        "preferences",
        "voice",
        "Female voice using Piper TTS."
    )


    remember(
        "projects",
        "rontogen_hardware",
        "Rontogen will eventually use an ESP32 as the physical interface while the laptop runs the AI brain."
    )


    print("\nStored memory:")
    print("--------------------------------")

    show_memory()


    print("\nProject memory:")
    print("--------------------------------")

    print(
        build_category_context(
            "projects"
        )
    )


    print("\nPreference memory:")
    print("--------------------------------")

    print(
        build_category_context(
            "preferences"
        )
    )


    print(
        "\nMemory manager test completed."
    )