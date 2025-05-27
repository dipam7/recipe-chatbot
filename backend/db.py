import os
import ssl
from typing import Dict, List
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# Get MongoDB connection string from environment variable
MONGODB_URI = os.getenv("MONGODB_URI")

# Create SSL context for better compatibility
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# Configure MongoDB client with explicit SSL settings
client = MongoClient(
    MONGODB_URI,
    ssl=True,
    ssl_cert_reqs=ssl.CERT_NONE,
    ssl_match_hostname=False,
    tlsAllowInvalidCertificates=True,
    tlsAllowInvalidHostnames=True,
    serverSelectionTimeoutMS=10000,
    connectTimeoutMS=10000,
    socketTimeoutMS=10000
)

db = client.get_database("recipe_chatbot")
conversations = db.get_collection("conversations")

def save_conversation(user_id: str, messages: List[Dict[str, str]]) -> str:
    """Save or update a conversation in the database."""
    result = conversations.update_one(
        {"user_id": user_id},
        {"$set": {"messages": messages}},
        upsert=True
    )
    return str(result.upserted_id or "updated")

def get_conversation(user_id: str) -> List[Dict[str, str]]:
    """Get a conversation from the database."""
    record = conversations.find_one({"user_id": user_id})
    if record:
        return record["messages"]
    return []