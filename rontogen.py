import json
import re
import threading
import queue
import time
import random

import requests
import numpy as np
import sounddevice as sd
from piper import PiperVoice

from english_coach import (
    get_correction,
    build_correction_message
)

from memory_manager import (
    load_memory,
    remember,
    build_memory_context,
    build_category_context,
    show_memory
)

from auto_memory import save_automatic_memory


# ============================================================
# CONFIGURATION
# ============================================================

MODEL = "qwen3:1.7b"

OLLAMA_URL = "http://localhost:11434/api/chat"

VOICE_MODEL = "en_US-amy-medium.onnx"

MAX_RECENT_MESSAGES = 8

# Delayed status is shown only when Qwen takes longer than this.
THINKING_STATUS_DELAY = 0.8

THINKING_STATUSES = [
    "Just a sec...",
    "Give me a moment...",
    "Thinking...",
    "One sec...",
    "Let me think...",
    "Working on it...",
]


# ============================================================
# MEMORY
# ============================================================

memory = load_memory()


# ============================================================
# LOAD VOICE
# ============================================================

print("Loading Rontogen's voice...")

try:

    voice = PiperVoice.load(
        VOICE_MODEL
    )

    print(
        "Voice loaded successfully!"
    )

except Exception as error:

    voice = None

    print(
        "Voice could not be loaded."
    )

    print(
        f"Voice error: {error}"
    )


# ============================================================
# SPEECH QUEUE
# ============================================================

speech_queue = queue.Queue()


def speech_worker():

    while True:

        text = speech_queue.get()


        if text is None:

            speech_queue.task_done()

            break


        try:

            if voice is None:
                continue


            if not text.strip():
                continue


            audio_chunks = []


            for chunk in voice.synthesize(text):

                audio_chunks.append(
                    chunk.audio_int16_bytes
                )


            if not audio_chunks:
                continue


            audio_data = np.frombuffer(
                b"".join(audio_chunks),
                dtype=np.int16
            )


            sd.play(
                audio_data,
                voice.config.sample_rate
            )

            sd.wait()


        except Exception as error:

            print(
                f"\n[Voice error: {error}]\n"
            )


        finally:

            speech_queue.task_done()


speech_thread = threading.Thread(
    target=speech_worker,
    daemon=True
)

speech_thread.start()


def speak(text):

    if not text:
        return


    if not text.strip():
        return


    speech_queue.put(
        text
    )


# ============================================================
# RESPONSE CLEANER
# ============================================================

EMOJI_PATTERN = re.compile(
    "["
    "\U0001F300-\U0001FAFF"
    "\U00002700-\U000027BF"
    "\U0001F1E6-\U0001F1FF"
    "\U00002600-\U000026FF"
    "\U00002B00-\U00002BFF"
    "]+",
    flags=re.UNICODE
)


STAGE_DIRECTION_PATTERN = re.compile(
    r"\*[^*\n]{1,100}\*"
)


BRACKET_ACTION_PATTERN = re.compile(
    r"\[[^\]\n]{1,100}\]"
)

GENERIC_ENDINGS = [

    "let me know if you need anything else.",

    "let me know if you need anything else!",

    "let me know if you need anything else?",

    "let me know if you need help with anything else.",

    "let me know if you need help with anything else!",

    "let me know if you need help with anything else?",

    "let me know if you want to chat more.",

    "let me know if you want to discuss your specific project details.",

    "let me know if you want to discuss your specific project details!",

    "let me know if you want to discuss your specific project details?",

    "let me know if you want to discuss the project.",

    "let me know if you want to discuss the project!",

    "let me know if you want to discuss the project?",

    "is there anything else i can help you with?",

    "is there anything else i can help with?",

    "how can i help you today?",

    "how can i assist you today?",

    "how may i assist you today?",

]


def remove_generic_ending(text):

    cleaned = text.strip()

    lower = cleaned.lower()


    for ending in GENERIC_ENDINGS:

        if lower.endswith(ending):

            cleaned = cleaned[
                :len(cleaned) - len(ending)
            ].rstrip()

            break


    return cleaned


def clean_response(text):

    if not text:

        return ""


    # --------------------------------------------------------
    # Remove stage directions
    # --------------------------------------------------------

    text = STAGE_DIRECTION_PATTERN.sub(
        "",
        text
    )


    # --------------------------------------------------------
    # Remove bracketed actions
    # --------------------------------------------------------

    text = BRACKET_ACTION_PATTERN.sub(
        "",
        text
    )


    # --------------------------------------------------------
    # Remove emojis
    # --------------------------------------------------------

    text = EMOJI_PATTERN.sub(
        "",
        text
    )


    # --------------------------------------------------------
    # Replace Unicode ellipsis
    # --------------------------------------------------------

    text = text.replace(
        "…",
        "..."
    )


    text = text.strip()


    # --------------------------------------------------------
    # Remove surrounding quotes
    # --------------------------------------------------------

    if len(text) >= 2:

        if (
            text[0] == '"'
            and text[-1] == '"'
        ):

            text = text[1:-1].strip()


        elif (
            text[0] == "'"
            and text[-1] == "'"
        ):

            text = text[1:-1].strip()


        elif (
            text[0] == "“"
            and text[-1] == "”"
        ):

            text = text[1:-1].strip()


    # --------------------------------------------------------
    # Remove generic endings
    # --------------------------------------------------------

    text = remove_generic_ending(
        text
    )


    # --------------------------------------------------------
    # Clean spaces
    # --------------------------------------------------------

    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )


    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text
    )


    return text.strip()


# ============================================================
# SENTENCE DETECTION
# ============================================================

def extract_sentences(buffer):

    sentences = []


    pattern = re.compile(
        r"(.+?[.!?]+(?:\s+|$))",
        re.DOTALL
    )


    while True:

        match = pattern.match(
            buffer
        )


        if not match:

            break


        sentence = match.group(1)


        buffer = buffer[
            len(sentence):
        ]


        sentence = clean_response(
            sentence
        )


        if sentence:

            sentences.append(
                sentence
            )


    return sentences, buffer


# ============================================================
# RESPONSE CONTROLLER
# ============================================================

def detect_response_context(
    user_input
):

    text = user_input.lower().strip()


    # --------------------------------------------------------
    # MEMORY QUESTIONS
    # --------------------------------------------------------

    memory_patterns = [

        r"\bwhat do you remember\b",

        r"\bdo you remember\b",

        r"\bwhat did i tell you\b",

        r"\bwhat have i told you\b",

        r"\bwhat do you know about me\b",

        r"\bmy preferences?\b",

        r"\bmy memory\b",

    ]


    for pattern in memory_patterns:

        if re.search(
            pattern,
            text
        ):

            # --------------------------------------------
            # Project-specific memory
            # --------------------------------------------

            project_words = [

                "project",
                "rontogen",
                "esp32",
                "physical device",
                "physical body",
                "ai brain",

            ]


            if any(
                word in text
                for word in project_words
            ):

                return "project_memory"


            # --------------------------------------------
            # Preference-specific memory
            # --------------------------------------------

            preference_words = [

                "voice",
                "preference",
                "preferences",

            ]


            if any(
                word in text
                for word in preference_words
            ):

                return "preference_memory"


            return "memory"


    # --------------------------------------------------------
    # STUDY / EDUCATION MEMORY
    # --------------------------------------------------------

    # Questions about what the USER studies must retrieve
    # only educational facts, not unrelated project memories.
    study_patterns = [
        r"\bwhat am i studying\b",
        r"\bwhat i am studying\b",
        r"\bwhat do i study\b",
        r"\bwhat i study\b",
        r"\bwhat am i learning\b",
        r"\bwhat i am learning\b",
        r"\bwhat do i learn\b",
        r"\bwhat i learn\b",
        r"\bwhat is my field\b",
        r"\bwhat is my degree\b",
        r"\bwhat course am i doing\b",
        r"\bwhat course i am doing\b",
        r"\bwhat am i studying on\b",
        r"\bwhat did i say i am studying\b",
        r"\bwhat did i say im studying\b",
    ]

    for pattern in study_patterns:
        if re.search(pattern, text):
            return "study_memory"

    # --------------------------------------------------------
    # PROJECT
    # --------------------------------------------------------

    project_words = [

        "rontogen",

        "my project",

        "the project",

        "esp32",

        "physical device",

        "physical body",

        "ai brain",

    ]


    if any(
        word in text
        for word in project_words
    ):

        return "project"


    # --------------------------------------------------------
    # GREETING
    # --------------------------------------------------------

    greeting_patterns = [

        r"^hi$",

        r"^hey$",

        r"^hello$",

        r"^hi bro$",

        r"^hey bro$",

        r"^hello bro$",

        r"^hey bro how are you$",

        r"^hey how are you$",

        r"^how are you$",

        r"^how are you doing$",

    ]


    for pattern in greeting_patterns:

        if re.fullmatch(
            pattern,
            text
        ):

            return "greeting"


    return "general"


# ============================================================
# GET RELEVANT MEMORY
# ============================================================

def get_relevant_memory(
    user_input
):

    context_type = detect_response_context(
        user_input
    )


    # --------------------------------------------------------
    # STUDY / EDUCATION MEMORY
    # --------------------------------------------------------

    if context_type == "study_memory":
        return build_category_context(
            "facts"
        )

    # --------------------------------------------------------
    # PROJECT MEMORY
    #
    # IMPORTANT:
    # Retrieve the complete projects category.
    # Do not use keyword search here.
    # --------------------------------------------------------

    if context_type == "project_memory":

        return build_category_context(
            "projects"
        )


    # --------------------------------------------------------
    # PROJECT REQUEST
    # --------------------------------------------------------

    if context_type == "project":

        return build_category_context(
            "projects"
        )


    # --------------------------------------------------------
    # PREFERENCE MEMORY
    # --------------------------------------------------------

    if context_type == "preference_memory":

        return build_category_context(
            "preferences"
        )


    # --------------------------------------------------------
    # GENERAL MEMORY REQUEST
    # --------------------------------------------------------

    if context_type == "memory":

        return build_memory_context(
            user_input
        )


    # --------------------------------------------------------
    # NORMAL CONVERSATION
    #
    # Only retrieve matching memories.
    # --------------------------------------------------------

    return build_memory_context(
        user_input
    )


# ============================================================
# LOCAL RESPONSES
# ============================================================

def get_local_response(
    user_input
):

    context = detect_response_context(
        user_input
    )


    # --------------------------------------------------------
    # GREETING
    #
    # No need to use Qwen for simple greetings.
    # --------------------------------------------------------

    if context == "greeting":

        text = user_input.lower().strip()


        if "how are you" in text:

            return (
                "Hey bro, I'm doing good."
            )


        return "Hey bro."


    return None


# ============================================================
# RONTOGEN PERSONALITY
# ============================================================

SYSTEM_PROMPT = """

You are Rontogen, the user's personal AI companion.

You are a familiar personal assistant and friend.

PERSONALITY:

- Be natural.
- Be casual when appropriate.
- You may use "bro" naturally.
- Use contractions.
- Be concise.
- Don't sound corporate.
- Don't sound robotic.
- Don't over-explain simple things.
- Don't repeat yourself.
- Don't use fake enthusiasm.
- Don't constantly ask questions.
- Don't end every response with a question.

IMPORTANT:

The user wants natural conversation.

Do not behave like a generic customer-support chatbot.

Never automatically say:

"How can I assist you today?"

"How may I assist you?"

"Let me know if you need anything else."

"Is there anything else I can help you with?"

Do not add unnecessary closing sentences.

SPEECH:

Your response will be spoken aloud.

Only produce words that should actually be spoken.

Never use:

- Emojis
- Emoticons
- Stage directions
- Actions inside asterisks
- Actions inside brackets
- Narration
- Fake sound effects

Never write:

"*grinning* Hey bro!"

Write:

"Hey bro!"

Never write:

"[laughing] That's funny."

Write:

"That's funny."

Do not wrap the response in quotation marks.

MEMORY:

Relevant long-term memory is supplied separately.

Treat supplied memory as the source of truth.

If something is present in supplied memory, you may use it.

If something is NOT present in supplied memory, do not invent it.

Never fabricate personal information.

Never fabricate project information.

Never claim to remember something that isn't supplied.

When asked what you remember, directly state the relevant information that is actually present.

PERSPECTIVE:
Memory may be stored as the user's original first-person statement.
When speaking to the user, preserve the meaning but convert the perspective naturally.

For example:
- Memory: "I am studying electrical and electronics engineering."
  User asks: "What am I studying?"
  Answer: "You're studying Electrical and Electronics Engineering."

- Memory: "I prefer a female voice for Rontogen."
  User asks: "What voice do I prefer?"
  Answer: "You prefer a female voice for Rontogen."

Do NOT copy the user's first-person wording as if Rontogen itself has that personal fact.
Do NOT say "I'm studying..." when the memory says the USER is studying something.
Use "you're", "you are", "you prefer", "your", etc. when referring to the user.

Do not say you don't have project details when project details are supplied.

RONTOGEN PROJECT:

Project information is supplied through memory.

Only use project information that is actually supplied.

Do not invent hardware, software, features, sensors, or future plans.

ENGLISH:

An external English Coach handles grammar corrections.

Do not turn every English mistake into a lesson.

Focus primarily on the user's actual conversation.

RESPONSE STYLE:

For simple conversation, respond simply.

For technical questions, explain clearly.

For personal conversation, sound natural.

Do not add unnecessary questions.

Do not add unnecessary closing sentences.

"""


# ============================================================
# SHORT-TERM CONVERSATION
# ============================================================

conversation_history = []


def build_messages(
    user_input
):

    recent_messages = conversation_history[
        -MAX_RECENT_MESSAGES:
    ]


    memory_context = get_relevant_memory(
        user_input
    )


    memory_instruction = (

        "\n\nRELEVANT LONG-TERM MEMORY:\n"

        + memory_context

        + "\n\n"

        "Use ONLY the supplied memory for personal facts. "
        "When supplied memory contains a first-person statement "
        "about the user, answer from the user's perspective. "
        "Convert 'I am' to 'you are' or 'you're', 'I prefer' "
        "to 'you prefer', and similar forms when speaking directly "
        "to the user. Do not treat the user's stored personal facts "
        "as Rontogen's own personal facts."

    )


    return [

        {
            "role": "system",

            "content": (
                SYSTEM_PROMPT
                + memory_instruction
            )
        }

    ] + recent_messages


# ============================================================
# SMART MEMORY STORAGE
# ============================================================

def remember_user_statement(
    text
):

    lower_text = text.lower()


    # --------------------------------------------------------
    # Determine whether this is a Rontogen project memory
    # --------------------------------------------------------

    project_keywords = [

        "rontogen",

        "esp32",

        "physical device",

        "physical body",

        "ai brain",

        "personal ai",

        "assistant project",

    ]


    is_project_memory = any(

        keyword in lower_text

        for keyword in project_keywords

    )


    # --------------------------------------------------------
    # PROJECT MEMORY
    # --------------------------------------------------------

    if is_project_memory:

        current_memory = load_memory()


        projects = current_memory.get(
            "projects",
            {}
        )


        if not isinstance(
            projects,
            dict
        ):

            projects = {}


        # ----------------------------------------------------
        # Prevent duplicates
        # ----------------------------------------------------

        for value in projects.values():

            if (
                str(value).lower()
                == text.lower()
            ):

                return


        number = 1


        while True:

            key = (
                f"rontogen_fact_{number}"
            )


            if key not in projects:

                break


            number += 1


        remember(
            "projects",
            key,
            text
        )


        return


    # --------------------------------------------------------
    # NORMAL FACT
    # --------------------------------------------------------

    current_memory = load_memory()


    facts = current_memory.get(
        "facts",
        {}
    )


    if not isinstance(
        facts,
        dict
    ):

        facts = {}


    for value in facts.values():

        if (
            str(value).lower()
            == text.lower()
        ):

            return


    number = 1


    while True:

        key = (
            f"fact_{number}"
        )


        if key not in facts:

            break


        number += 1


    remember(
        "facts",
        key,
        text
    )


# ============================================================
# DELAYED THINKING STATUS
# ============================================================

def start_thinking_status():
    state = {"done": False}

    def worker():
        time.sleep(THINKING_STATUS_DELAY)

        if state["done"]:
            return

        message = random.choice(THINKING_STATUSES)

        print(
            f"\nRontogen: {message}",
            flush=True
        )

        # Speak the status too. It is queued before the final
        # response, so the user hears it while waiting.
        speak(message)

    thread = threading.Thread(
        target=worker,
        daemon=True
    )
    thread.start()

    return state


# ============================================================
# START RONTOGEN
# ============================================================

print()

print("=" * 50)

print("             RONTOGEN")

print("       Your Personal AI Companion")

print("=" * 50)

print(
    "Type 'exit' to close Rontogen."
)

print(
    "Type 'show memory' to see what Rontogen remembers."
)

print()


# ============================================================
# MAIN LOOP
# ============================================================

while True:

    user_input = input(
        "You: "
    )


    # ========================================================
    # EXIT
    # ========================================================

    if user_input.lower().strip() == "exit":

        goodbye = (
            "See you later, bro!"
        )


        print(
            f"\nRontogen: {goodbye}\n"
        )


        speak(
            goodbye
        )


        speech_queue.join()


        break


    # ========================================================
    # SHOW MEMORY
    # ========================================================

    if user_input.lower().strip() == "show memory":

        print(
            "\n----- RONTOGEN MEMORY -----"
        )


        show_memory()


        print(
            "\n---------------------------\n"
        )


        continue


    # ========================================================
    # EMPTY INPUT
    # ========================================================

    if not user_input.strip():

        continue


    lower_text = user_input.lower()


    # ========================================================
    # REMEMBER THAT
    # ========================================================

    if lower_text.startswith(
        "remember that "
    ):

        statement = user_input[
            len("remember that "):
        ].strip()


        if statement:

            remember_user_statement(
                statement
            )


        reply = (
            "Got it bro. I'll remember that."
        )


        print(
            f"\nRontogen: {reply}\n"
        )


        speak(
            reply
        )


        continue


    # ========================================================
    # AUTOMATIC MEMORY
    # ========================================================

    # Check normal conversation for useful long-term information.
    # Explicit "remember that..." commands are handled above.
    automatic_memory = save_automatic_memory(
        user_input
    )


    # ========================================================
    # ENGLISH COACH
    # ========================================================

    correction = get_correction(
        user_input
    )


    if correction:

        correction_message = (
            build_correction_message(
                user_input,
                correction
            )
        )


        print(
            f"\nRontogen: {correction_message}\n"
        )


        speak(
            correction_message
        )


    # ========================================================
    # LOCAL RESPONSE CONTROLLER
    # ========================================================

    local_response = get_local_response(
        user_input
    )


    if local_response:

        print(
            f"\nRontogen: {local_response}\n"
        )


        speak(
            local_response
        )


        conversation_history.append(
            {
                "role": "user",
                "content": user_input
            }
        )


        conversation_history.append(
            {
                "role": "assistant",
                "content": local_response
            }
        )


        if len(
            conversation_history
        ) > MAX_RECENT_MESSAGES:

            conversation_history = (
                conversation_history[
                    -MAX_RECENT_MESSAGES:
                ]
            )


        speech_queue.join()


        continue


    # ========================================================
    # ADD USER MESSAGE
    # ========================================================

    conversation_history.append(
        {
            "role": "user",
            "content": user_input
        }
    )


    # ========================================================
    # ASK QWEN
    # ========================================================

    # Start a delayed status watcher. Fast replies stay silent.
    thinking_state = start_thinking_status()

    try:

        response = requests.post(

            OLLAMA_URL,

            json={

                "model": MODEL,

                "messages": build_messages(
                    user_input
                ),

                "stream": True

            },

            stream=True,

            timeout=120
        )


        response.raise_for_status()

        # Qwen has started responding.
        thinking_state["done"] = True

        reply_parts = []

        sentence_buffer = ""


        print(
            "\nRontogen: ",
            end="",
            flush=True
        )


        # ====================================================
        # STREAM RESPONSE
        # ====================================================

        for line in response.iter_lines():

            if not line:

                continue


            try:

                data = json.loads(
                    line.decode(
                        "utf-8"
                    )
                )


            except json.JSONDecodeError:

                continue


            if (
                "message" in data
                and "content" in data["message"]
            ):

                token = data[
                    "message"
                ][
                    "content"
                ]


                reply_parts.append(
                    token
                )


                sentence_buffer += (
                    token
                )


                sentences, sentence_buffer = (
                    extract_sentences(
                        sentence_buffer
                    )
                )


                for sentence in sentences:

                    if not sentence:

                        continue


                    print(
                        sentence + " ",
                        end="",
                        flush=True
                    )


                    speak(
                        sentence
                    )


        # ====================================================
        # COMPLETE RESPONSE
        # ====================================================

        raw_reply = "".join(
            reply_parts
        ).strip()


        # ====================================================
        # REMAINING TEXT
        # ====================================================

        remaining = clean_response(
            sentence_buffer
        )


        if remaining:

            print(
                remaining,
                end="",
                flush=True
            )


            speak(
                remaining
            )


        # ====================================================
        # CLEAN RESPONSE
        # ====================================================

        clean_reply = clean_response(
            raw_reply
        )


        # ====================================================
        # WAIT FOR SPEECH
        # ====================================================

        speech_queue.join()


        print(
            "\n"
        )


        # ====================================================
        # SAVE ASSISTANT RESPONSE
        # ====================================================

        conversation_history.append(
            {
                "role": "assistant",
                "content": clean_reply
            }
        )


        # ====================================================
        # LIMIT SHORT-TERM MEMORY
        # ====================================================

        if len(
            conversation_history
        ) > MAX_RECENT_MESSAGES:

            conversation_history = (
                conversation_history[
                    -MAX_RECENT_MESSAGES:
                ]
            )


    # ========================================================
    # CONNECTION ERROR
    # ========================================================

    except requests.exceptions.RequestException as error:

        thinking_state["done"] = True

        if conversation_history:

            conversation_history.pop()


        print(
            "\nRontogen: I can't reach my AI brain right now."
        )


        print(
            f"Error: {error}\n"
        )
