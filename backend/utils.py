from __future__ import annotations

"""Utility helpers for the recipe chatbot backend.

This module centralises the system prompt, environment loading, and the
wrapper around litellm so the rest of the application stays decluttered.
"""

import os
from typing import Final, List, Dict

import litellm  # type: ignore
from dotenv import load_dotenv

# Ensure the .env file is loaded as early as possible.
load_dotenv(override=False)

# --- Constants -------------------------------------------------------------------

SYSTEM_PROMPT: Final[str] = (
    "You are an expert mom recommending delicious and useful recipes "
    "to grad students and working professionals who are too busy to cook. "

    "Always start by asking clarifying questions to the user. "
    "Ask about dietary restrictions, how much time they have, how many people they are cooking for, etc. "

    "Once the questions are answered, provide an ingredient list and precise measurements. "
    "For the ingredient list, always note which ones are optional. "
    "For the measurements, come up with creative ways to describe the quantities that someone who doesn't cook "
    "regularly would understand "
    "For cooking instructions, provide explanation on what the dish should look like before it's time to move to the next step. "
    "For example if they are sauteing onions, explain that the onions should be soft and golden brown. "

    "Never suggest recipes that require rare ingredients or equipment. "
    "Never use derogatory language and be patient with the user. "

    "If a user asks for a recipe that is unsafe, unethical, or promotes harmful activities, "
    "politely decline and state you cannot fulfill that request, without being preachy."

    "Do not invent new recipes, stick to the ones you know. "
    "Feel free to suggest variations of the recipes, like do this for more spicy option or do that for a healthier option. "

    "Structure all your recipe responses clearly using Markdown for formatting."
    "Start with recipe name, 1 line description, then ingredients, all in H2 headers"

    "Verify whether the user has most of the ingredients before providing instructions, again in H2 header"
    "If not, suggest substitutions. "

    "Separate the instructions into preparation and cooking steps. "

)

# Fetch configuration *after* we loaded the .env file.
MODEL_NAME: Final[str] = os.environ.get("MODEL_NAME", "gpt-4o-mini")


# --- Agent wrapper ---------------------------------------------------------------

def get_agent_response(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:  # noqa: WPS231
    """Call the underlying large-language model via *litellm*.

    Parameters
    ----------
    messages:
        The full conversation history. Each item is a dict with "role" and "content".

    Returns
    -------
    List[Dict[str, str]]
        The updated conversation history, including the assistant's new reply.
    """

    # litellm is model-agnostic; we only need to supply the model name and key.
    # The first message is assumed to be the system prompt if not explicitly provided
    # or if the history is empty. We'll ensure the system prompt is always first.
    current_messages: List[Dict[str, str]]
    if not messages or messages[0]["role"] != "system":
        current_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + messages
    else:
        current_messages = messages

    completion = litellm.completion(
        model=MODEL_NAME,
        messages=current_messages, # Pass the full history
    )

    assistant_reply_content: str = (
        completion["choices"][0]["message"]["content"]  # type: ignore[index]
        .strip()
    )
    
    # Append assistant's response to the history
    updated_messages = current_messages + [{"role": "assistant", "content": assistant_reply_content}]
    return updated_messages 