import os
from dotenv import load_dotenv
load_dotenv()  # reads .env in the current directory

from uagents_core.utils.registration import (
    register_chat_agent,
    RegistrationRequestCredentials,
)

register_chat_agent(
    "talantis-atlas",
    "https://talantis-atlas-uagent-chat-protocol.onrender.com/submit",
    active=True,
    credentials=RegistrationRequestCredentials(
        agentverse_api_key=os.environ["AGENTVERSE_KEY"],
        agent_seed_phrase=os.environ["AGENT_SEED_PHRASE"],
    ),
)