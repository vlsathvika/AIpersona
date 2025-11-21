import os
import json
import streamlit as st
from fpdf import FPDF
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate
    USE_REPORTLAB = True
except Exception:
    USE_REPORTLAB = False
import openai
try:
    from openai.error import OpenAIError
except Exception:
    # Some openai package versions may not expose openai.error; fall back to base Exception
    OpenAIError = Exception

# Detect new OpenAI Python v1+ interface (OpenAI client)
try:
    from openai import OpenAI as OpenAIClient
    NEW_OPENAI_CLIENT = True
except Exception:
    OpenAIClient = None
    NEW_OPENAI_CLIENT = False


# Function to convert JSON chat history to PDF
def convert_json_to_pdf_bytes(json_data):
    """Return PDF bytes for given chat history. Prefer reportlab for UTF-8 support, fallback to FPDF."""
    if USE_REPORTLAB:
        from io import BytesIO
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        for message in json_data:
            role = message.get('role', 'assistant').capitalize()
            content = message.get('content', '')
            # escape content for Paragraph
            ptext = f"<b>{role}:</b> {content}"
            story.append(Paragraph(ptext, styles['Normal']))
            story.append(Paragraph('<br/>', styles['Normal']))
        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
    else:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)
        
        for message in json_data:
            role = message.get('role', 'assistant')
            content = message.get('content', '')
            # Encode to latin-1 with replacement to avoid crashes
            content = content.encode('latin-1', 'replace').decode('latin-1')
            pdf.multi_cell(0, 10, f"{role.capitalize()}: {content}", border=0, align='L', fill=False)
        from io import BytesIO
        buffer = BytesIO()
        pdf.output(buffer)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
    



# Read OpenAI API key from Streamlit secrets or environment (safe access)
openai_api_key = None
try:
    # Access st.secrets in a safe way; it may raise if no secrets file exists
    if st.secrets and "OPENAI_API_KEY" in st.secrets:
        openai_api_key = st.secrets["OPENAI_API_KEY"]
except Exception:
    # No Streamlit secrets configured; fall back to environment
    openai_api_key = None

if not openai_api_key:
    openai_api_key = os.environ.get("OPENAI_API_KEY")

# If still not found, allow entering a key at runtime for testing (will not be saved)
if not openai_api_key:
    test_key = st.text_input("Enter OpenAI API key for testing (will not be used persistently):", type="password")
    if test_key:
        openai_api_key = test_key
        st.info("Using API key provided via the UI for this session only.")

if not openai_api_key:
    st.warning("OpenAI API key not found. Add it to Streamlit secrets as OPENAI_API_KEY, set the OPENAI_API_KEY environment variable, or paste it into the test field.")

openai.api_key = openai_api_key

# Create client for new SDK if available
client = None
if NEW_OPENAI_CLIENT:
    try:
        # instantiate with explicit API key so it works even if env isn't set
        client = OpenAIClient(api_key=openai_api_key)
    except Exception:
        # fallback to default constructor which reads env
        try:
            client = OpenAIClient()
        except Exception:
            client = None

# Define the characters with their segments
characters = {
    "Balance Seekers": {
        "Name":" Ben",
        "Demographics": "Typically middle-aged, balanced gender distribution, moderate income.",
        "Personality": "Balanced, health-conscious, moderate.",
        "Health Status": "Generally healthy.",
        "Provider Utilization": "Moderate.",
        "Insurance": "Typically insured.",
        "Health Insurance Coverage": "Comprehensive.",
        "Chronic Conditions": "Few or none.",
        "Words/Phrases (recommended)": "Balance, wellness, moderation.",
        "Words to Lose": "Extreme, neglect."
    },
    "Priority Juggler": {
        "Name":"Paige",
        "Demographics": "Often parents, middle-aged, moderate to high income.",
        "Personality": "Busy, caring, multitasker.",
        "Health Status": "Varies.",
        "Provider Utilization": "Inconsistent.",
        "Insurance": "Varies.",
        "Health Insurance Coverage": "Varies.",
        "Chronic Conditions": "Possible.",
        "Words/Phrases (recommended)": "Manage, prioritize, balance.",
        "Words to Lose": "Neglect, ignore."
    },
    "Willful Endurer": {
        "Name":"Willy",
        "Demographics": "Older adults, often retired, varied income.",
        "Personality": "Resilient, determined, enduring.",
        "Health Status": "Chronic conditions.",
        "Provider Utilization": "High.",
        "Insurance": "Typically insured.",
        "Health Insurance Coverage": "Comprehensive.",
        "Chronic Conditions": "Multiple.",
        "Words/Phrases (recommended)": "Endure, resilience, strength.",
        "Words to Lose": "Weak, give up."
    },
    "Self Achiever": {
        "Name":" Sarah",
        "Demographics": "Young to middle-aged adults, high income, career-focused.",
        "Personality": "Goal-oriented, proactive, ambitious.",
        "Health Status": "Generally healthy.",
        "Provider Utilization": "Proactive.",
        "Insurance": "Typically insured.",
        "Health Insurance Coverage": "Comprehensive.",
        "Chronic Conditions": "Few or none.",
        "Words/Phrases (recommended)": "Achieve, proactive, success.",
        "Words to Lose": "Lazy, passive."
    },
    "Trustful Responder": {
        "Name":" Tim",
        "Demographics": "Varied age, typically insured, moderate to high income.",
        "Personality": "Trusting, compliant, responsive.",
        "Health Status": "Varies.",
        "Provider Utilization": "High.",
        "Insurance": "Typically insured.",
        "Health Insurance Coverage": "Comprehensive.",
        "Chronic Conditions": "Possible.",
        "Words/Phrases (recommended)": "Trust, follow, reliable.",
        "Words to Lose": "Skeptical, ignore."
    },
    "General Bot": {
        "Name":"Brandience",
        "Demographics": "No Age Restriction,varied Income",
        "Personality": "open,honest,responsive.",
        "Health Status": "Varies.",
        "Provider Utilization": "High.",
        "Insurance": "Typically insured.",
        "Health Insurance Coverage": "Comprehensive.",
        "Chronic Conditions": "Not possible",
    }
}

if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

def authenticate(password):
    if password == 'AIpersona123':
        st.session_state['authenticated'] = True
    else:
        st.error("Wrong password")

if not st.session_state['authenticated']:
    password = st.text_input("Enter Password", type="password")
    if st.button("Submit"):
        authenticate(password)
else:
    if "messages" not in st.session_state:
        # Try to load an existing chat history file
        if os.path.exists('chat_history.json'):
            try:
                with open('chat_history.json', 'r', encoding='utf-8') as f:
                    existing = json.load(f)
                    if isinstance(existing, list) and existing:
                        st.session_state["messages"] = existing
                    else:
                        st.session_state["messages"] = [{"role": "system", "content": "You are a friendly agent. Respond in the voice and behaviour of the selected character."}]
            except Exception:
                st.session_state["messages"] = [{"role": "system", "content": "You are a friendly agent. Respond in the voice and behaviour of the selected character."}]
        else:
            st.session_state["messages"] = [{"role": "system", "content": "You are a friendly agent. Respond in the voice and behaviour of the selected character."}]

    # Helper: per-character history filename
    def history_filename_for(character_name):
        safe = character_name.replace(' ', '_').lower()
        return f"chat_history_{safe}.json"

    # Function to save the chat history to a file (per-character)
    def save_chat_history_to_file(character_name=None):
        try:
            if character_name is None:
                character_name = st.session_state.get('current_character', None) or character
            filename = history_filename_for(character_name)
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(st.session_state["messages"], f, ensure_ascii=False)
        except Exception as e:
            st.error(f"Failed to save chat history: {e}")

    # Function to append the response to the chat history (supports dicts and objects)
    def append_to_chat_history(response):
        if isinstance(response, dict):
            role = response.get('role', 'assistant')
            content = response.get('content') or response.get('text') or ''
        else:
            role = getattr(response, 'role', 'assistant')
            content = getattr(response, 'content', '')

        st.session_state["messages"].append({"role": role, "content": content})
        # Persist immediately (save under current character)
        try:
            save_chat_history_to_file()
        except Exception:
            # last-resort fallback to a generic file
            try:
                with open('chat_history.json', 'w', encoding='utf-8') as f:
                    json.dump(st.session_state["messages"], f, ensure_ascii=False)
            except Exception:
                pass

    # Normalize a choice object/dict from different SDKs into a simple message dict
    def normalize_choice_to_message(choice):
        role = None
        content = ''
        try:
            if isinstance(choice, dict):
                # choice may contain a 'message' dict
                message = choice.get('message') or choice.get('delta') or {}
                if isinstance(message, dict):
                    role = message.get('role')
                    # content can be string or nested
                    content = message.get('content') or ''
                    # if content is a list, join
                    if isinstance(content, list):
                        content = ''.join([str(x) for x in content])
                else:
                    content = choice.get('text') or ''
                    role = choice.get('role')
            else:
                # object with attributes
                message = getattr(choice, 'message', None)
                if message is not None:
                    role = getattr(message, 'role', None)
                    # message.content may be a string or list
                    content = getattr(message, 'content', None)
                    if content is None:
                        # try common alternative attribute names
                        content = getattr(message, 'text', '') or ''
                    if isinstance(content, list):
                        content = ''.join([str(x) for x in content])
                else:
                    content = getattr(choice, 'text', '') or ''
                    role = getattr(choice, 'role', None)
        except Exception:
            content = ''

        if not role:
            role = 'assistant'
        if content is None:
            content = ''
        return {"role": role, "content": content}

    # Sidebar: character controls
    lock_character = st.sidebar.checkbox("Lock character (prevent switching)", value=False)
    auto_clear_on_change = st.sidebar.checkbox("Auto-clear conversation when changing character", value=False)
    include_examples = st.sidebar.checkbox("Include few-shot examples in system prompt", value=False)

    # Ensure current_character exists
    if 'current_character' not in st.session_state:
        st.session_state['current_character'] = list(characters.keys())[0]

    char_list = list(characters.keys())
    # If locked, force the selectbox to display the current character index
    if lock_character:
        default_index = char_list.index(st.session_state['current_character']) if st.session_state['current_character'] in char_list else 0
        selected = st.sidebar.selectbox("Select a Character", char_list, index=default_index)
    else:
        # allow user to pick; default to current_character
        default_index = char_list.index(st.session_state['current_character']) if st.session_state['current_character'] in char_list else 0
        selected = st.sidebar.selectbox("Select a Character", char_list, index=default_index)

    # Determine active character without writing to widget-backed session_state keys
    if lock_character:
        character = st.session_state['current_character']
        if selected != character:
            st.warning(f"Character is locked. Staying with '{character}'. Uncheck 'Lock character' to change.")
    else:
        character = selected
        # If changed, load or clear history as requested
        if character != st.session_state.get('current_character'):
            attempted = character
            if auto_clear_on_change:
                st.session_state['messages'] = [{"role": "system", "content": ""}]
                try:
                    fname = history_filename_for(attempted)
                    if os.path.exists(fname):
                        os.remove(fname)
                except Exception:
                    pass
            else:
                try:
                    fname = history_filename_for(attempted)
                    if os.path.exists(fname):
                        with open(fname, 'r', encoding='utf-8') as f:
                            loaded = json.load(f)
                            if isinstance(loaded, list) and loaded:
                                st.session_state['messages'] = loaded
                except Exception:
                    st.session_state['messages'] = [{"role": "system", "content": ""}]

            st.session_state['current_character'] = character

    # Get the bot's name for the selected character
    bot_name = characters[character]["Name"]

    # Model / response tuning controls in the sidebar (hidden by default for non-technical users)
    # Provide sensible defaults and let advanced users reveal controls explicitly
    temp = 0.7
    top_p = 1.0
    freq_pen = 0.0
    pres_pen = 0.0
    max_tokens = 1024

    st.sidebar.write("Model settings: using sensible defaults for non-technical users.")
    st.sidebar.write(f"Temperature: {temp} (default)")

    show_advanced = st.sidebar.checkbox("Show advanced model settings", value=False)
    if show_advanced:
        with st.sidebar.expander("Advanced model settings", expanded=True):
            temp = st.slider("Temperature", 0.0, 1.0, temp, 0.05, help="Higher = more creative; lower = more deterministic")
            top_p = st.slider("top_p", 0.0, 1.0, top_p, 0.05)
            freq_pen = st.slider("frequency_penalty", -2.0, 2.0, freq_pen, 0.1)
            pres_pen = st.slider("presence_penalty", -2.0, 2.0, pres_pen, 0.1)
            max_tokens = st.number_input("Max tokens", min_value=64, max_value=4096, value=max_tokens, step=64)

    st.title(f"🧑‍💻 {bot_name} Online 💬 Chatbot")
    st.write(f"My name is {bot_name}🤖. I know many things, ask me anything you like, but please, don't ask me stupid questions❓")

    # Display character description
    st.header(f"{character}")
    for key, value in characters[character].items():
        st.subheader(key)
        st.write(value)

    # Chat UI
    st.subheader("Conversation")

    # Helper to build a system message from the chosen character
    def build_system_message(character_key):
        attrs = characters.get(character_key, {})
        parts = [f"You are {attrs.get('Name', 'the assistant')}."]
        for k, v in attrs.items():
            if k == 'Name':
                continue
            parts.append(f"{k}: {v}.")
        # Add persona-specific guidance for wording
        recommended = attrs.get('Words/Phrases (recommended)') or attrs.get('Words/Phrases')
        avoid = attrs.get('Words to Lose') or attrs.get('Words to Avoid')
        if recommended:
            parts.append(f"Prefer using these words/phrases: {recommended}.")
        if avoid:
            parts.append(f"Avoid using these words/phrases: {avoid}.")

        parts.append("Answer concisely, stay in character, and be accurate. Provide 2-3 actionable, persona-aligned suggestions when asked for advice. If medical advice is requested, provide general info and recommend consulting a professional.")
        # Optionally include few-shot examples to shape output
        try:
            if include_examples:
                parts.append("Examples:")
                # A generic example that demonstrates numbered, actionable suggestions
                parts.append("User: I'm having trouble sleeping sometimes.\nAssistant: 1) Create a consistent bedtime routine and stick to it; explain why. 2) Limit caffeine after midday; explain why. 3) Try light exercise earlier in the day; explain why.")
                parts.append("User: I want to be more productive.\nAssistant: 1) Break tasks into 25-minute focused intervals (Pomodoro); explain briefly. 2) Prioritize top 3 tasks each day; explain briefly.")
        except Exception:
            pass
        return ' '.join(parts)

    # Ensure the current system message reflects the selected character
    system_msg = build_system_message(character)
    if st.session_state["messages"]:
        if st.session_state["messages"][0].get('role') == 'system':
            st.session_state["messages"][0]['content'] = system_msg
        else:
            st.session_state["messages"].insert(0, {"role": "system", "content": system_msg})

    # Display the conversation (excluding system messages)
    for msg in st.session_state["messages"]:
        if msg.get('role') == 'system':
            continue
        try:
            st.chat_message(msg.get('role')).write(msg.get('content'))
        except Exception:
            st.write(f"{msg.get('role')}: {msg.get('content')}")

    # Collect user input via chat input (Streamlit chat-like UI)
    user_input = st.chat_input(f"Message as {character}...")
    if user_input:
        # append user message and display
        st.session_state["messages"].append({"role": "user", "content": user_input})
        st.chat_message("user").write(user_input)

        # Call the model
        try:
            with st.spinner("Thinking..."):
                if client is not None:
                    response = client.chat.completions.create(
                        model="gpt-4o",
                        messages=st.session_state["messages"],
                        temperature=temp,
                        max_tokens=max_tokens,
                        top_p=top_p,
                        frequency_penalty=freq_pen,
                        presence_penalty=pres_pen,
                    )
                else:
                    response = openai.ChatCompletion.create(
                        model="gpt-4o",
                        messages=st.session_state["messages"],
                        temperature=temp,
                        max_tokens=max_tokens,
                        top_p=top_p,
                        frequency_penalty=freq_pen,
                        presence_penalty=pres_pen,
                    )

            # Normalize and show assistant reply
            choice = None
            try:
                choice = response['choices'][0]
            except Exception:
                try:
                    choice = response.choices[0]
                except Exception:
                    choice = None

            msg = normalize_choice_to_message(choice)
            append_to_chat_history(msg)
            st.chat_message("assistant").write(msg["content"])

        except OpenAIError as e:
            st.error(f"OpenAI API error: {e}")
        except Exception as e:
            st.error(f"Unexpected error: {e}")

    # Button to download chat history as PDF
    if st.button("Download Chat History as PDF"):
        # Prefer per-character history file if present
        current_char = st.session_state.get('current_character', character)
        fname = history_filename_for(current_char)
        try:
            if os.path.exists(fname):
                with open(fname, 'r', encoding='utf-8') as f:
                    chat_history_json = json.load(f)
            else:
                chat_history_json = st.session_state.get('messages', [])

            pdf_bytes = convert_json_to_pdf_bytes(chat_history_json)

            st.download_button(label="Download PDF", data=pdf_bytes, file_name=f"chat_history_{current_char.replace(' ', '_')}.pdf", mime="application/pdf")
        except Exception as e:
            st.error(f"Failed to generate PDF: {e}")

    # Clear chat history (for current character)
    if st.button("Clear Chat History"):
        st.session_state["messages"] = [{"role": "system", "content": build_system_message(character)}]
        try:
            fname = history_filename_for(character)
            if os.path.exists(fname):
                os.remove(fname)
        except Exception:
            pass
        # persist cleared state for this character
        try:
            save_chat_history_to_file(character)
        except Exception:
            pass
        st.success("Chat history cleared for current character.")
    
