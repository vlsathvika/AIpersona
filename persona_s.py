import os
import json
import streamlit as st
from fpdf import FPDF
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
def convert_json_to_pdf(json_data):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    for message in json_data:
        role = message['role']
        content = message['content']
        
        # Encode content to utf-8
        content = content.encode('latin-1', 'replace').decode('latin-1')
        
        pdf.multi_cell(0, 10, f"{role.capitalize()}: {content}", border=0, align='L', fill=False)
    
    return pdf
    



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

    # Function to save the chat history to a file
    def save_chat_history_to_file(filename):
        try:
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
        # Persist immediately
        save_chat_history_to_file('chat_history.json')

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

    # Select a character
    character = st.sidebar.selectbox("Select a Character", list(characters.keys()))

    # Get the bot's name for the selected character
    bot_name = characters[character]["Name"]

    # Model / response tuning controls in the sidebar
    with st.sidebar.expander("Model settings"):
        temp = st.slider("Temperature", 0.0, 1.0, 0.7, 0.05, help="Higher = more creative; lower = more deterministic")
        top_p = st.slider("top_p", 0.0, 1.0, 1.0, 0.05)
        freq_pen = st.slider("frequency_penalty", -2.0, 2.0, 0.0, 0.1)
        pres_pen = st.slider("presence_penalty", -2.0, 2.0, 0.0, 0.1)
        max_tokens = st.number_input("Max tokens", min_value=64, max_value=4096, value=1024, step=64)

    st.title(f"🧑‍💻 {bot_name} Online 💬 Chatbot")
    st.write(f"My name is {bot_name}🤖. I know many things, ask me anything you like, but please, don't ask me stupid questions❓")

    # Display character description
    st.header(f"{character}")
    for key, value in characters[character].items():
        st.subheader(key)
        st.write(value)

    # General questions section
    st.subheader("Ask General Questions")
    general_question = st.text_input("Ask a general question about this character's behaviors or values:")
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
        return ' '.join(parts)

    # Ensure the current system message reflects the selected character
    system_msg = build_system_message(character)
    if st.session_state["messages"]:
        if st.session_state["messages"][0].get('role') == 'system':
            st.session_state["messages"][0]['content'] = system_msg
        else:
            st.session_state["messages"].insert(0, {"role": "system", "content": system_msg})

    # Ask a general question using OpenAI
    if st.button("Ask General Question"):
        if general_question:
            user_msg = f"As a {character}, {general_question}"
            st.session_state["messages"].append({"role": "user", "content": user_msg})
            st.chat_message("user").write(general_question)

            try:
                # Use new OpenAI client if available, otherwise fall back to old openai.ChatCompletion
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

                # Normalize the choice/message extraction across SDK versions
                choice = None
                try:
                    choice = response['choices'][0]
                except Exception:
                    try:
                        choice = response.choices[0]
                    except Exception:
                        choice = None

                # Normalize choice into a plain message dict and display safely
                msg = normalize_choice_to_message(choice)
                append_to_chat_history(msg)
                st.chat_message("assistant").write(msg["content"])

            except OpenAIError as e:
                st.error(f"OpenAI API error: {e}")
            except Exception as e:
                st.error(f"Unexpected error: {e}")
        else:
            st.write("Please enter a question.")

    # Advertising creative section
    st.subheader("Test Opinions on Advertising Creative")
    creative_input = st.text_input("Enter a headline or description of an image for the character to review:")

    # Get OpenAI response for advertising creative
    if st.button("Test Creative"):
        if creative_input:
            user_msg = f"As a {character}, what do you think about this: {creative_input}"
            st.session_state["messages"].append({"role": "user", "content": user_msg})
            st.chat_message("user").write(creative_input)

            try:
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

                # Normalize the choice/message extraction across SDK versions
                choice = None
                try:
                    choice = response['choices'][0]
                except Exception:
                    try:
                        choice = response.choices[0]
                    except Exception:
                        choice = None

                # Normalize choice into a plain message dict and display safely
                msg = normalize_choice_to_message(choice)
                append_to_chat_history(msg)
                st.chat_message("assistant").write(msg["content"])

            except OpenAIError as e:
                st.error(f"OpenAI API error: {e}")
            except Exception as e:
                st.error(f"Unexpected error: {e}")
        else:
            st.write("Please enter a headline or description.")

    # Button to download chat history as PDF
    if st.button("Download Chat History as PDF"):
        with open('chat_history.json', 'r', encoding='utf-8') as f:
            chat_history_json = json.load(f)
        
        pdf = convert_json_to_pdf(chat_history_json)
        
        pdf_output_path = 'chat_history.pdf'
        
        pdf.output(pdf_output_path)
        
        with open(pdf_output_path, 'rb') as f:
            pdf_data = f.read()
        
        st.download_button(label="Download PDF", data=pdf_data, file_name="chat_history.pdf", mime="application/pdf")
    
    # Clear chat history
    if st.button("Clear Chat History"):
        st.session_state["messages"] = [{"role": "system", "content": build_system_message(character)}]
        try:
            if os.path.exists('chat_history.json'):
                os.remove('chat_history.json')
        except Exception:
            pass
        st.success("Chat history cleared.")
    
