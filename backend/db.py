import os
from typing import Dict, List
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# Get MongoDB connection string from environment variable
MONGODB_URI = os.getenv("MONGODB_URI")

# Configure MongoDB client with explicit SSL settings
client = MongoClient(
    MONGODB_URI,
    tls=True,
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