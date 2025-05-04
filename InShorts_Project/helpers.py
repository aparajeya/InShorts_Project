import re
import json
import requests
from pymongo import MongoClient
from django.conf import settings
from math import radians, sin, cos, sqrt, atan2
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError


# MongoDB client setup
client = MongoClient(settings.MONGO_URI)
db = client[settings.MONGO_DB]
articles_collection = db["articles"]

GROQ_API_KEY = "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"
url = "https://api.groq.com/openai/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json",
}

# and do not create nested JSON


def call_groq_api(input_query):
    system_prompt = """
      You are a news query processor. Your task is to extract structured information from user queries to help route them to the correct news retrieval system.

      Given a query:
      1. Extract named entities (people, organizations, locations, events).
      2. Identify the user's intent. Use these categories:
        - "nearby" → if a location is mentioned.
        - "source" → if a news source is mentioned (e.g., CNN, BBC, New York Times).
        - "category" → if the query refers to a topic like technology, politics, etc.
        - You may return multiple intents.
      3. Extract relevant concepts like technology, business, politics, etc.

      Output your answer strictly in the following JSON format:
      {
        "entities": [...],
        "intent": [...],
        "concepts": [...]
      }
      Do NOT include explanations or any text outside the JSON.
      """
    data = {
        "model": "llama3-8b-8192",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": input_query},
        ],
        "temperature": 0.3,
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        reply = response.json()["choices"][0]["message"]["content"]
        try:
            # Extract JSON from the reply
            json_str = re.search(r"\{.*\}", reply, re.DOTALL).group(0)
            return json.loads(json_str)
        except Exception as e:
            print("Failed to parse JSON:\n", reply)
            raise e
        # print("REPLY IS ",reply)
        # return (reply)  # Parsing the response string to dict
    else:
        return None


def generate_llm_summary(title, description, article_url):
    system_prompt = """
      You are a news summarization assistant. Your task is to write a short, clear, and informative summary of a news article given its title, description, and URL.

      Requirements:
      - The summary should be 60 to 70 words long.
      - Summarize the content of the URL, using the title and description for context.
      - Maintain an objective and informative tone.
      - Do not include any explanation or commentary outside the summary paragraph.
      - Do not mention the title, description, or the fact that it's a summary.

      Only return the summary paragraph as plain text.
      """

    data = {
        "model": "llama3-8b-8192",
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"URL: {article_url}",
            },
        ],
        "temperature": 0.4,
    }
    # "content": f"Title: {title}\nDescription: {description}\nURL: {article_url}",

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        reply = response.json()["choices"][0]["message"]["content"].strip()
        return reply
    else:
        return "Summary unavailable due to API error."


def calculate_distance(lat1, lon1, lat2, lon2):
    # Haversine formula to calculate distance between two lat-long points
    R = 6371  # Radius of Earth in kilometers
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    )
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c  # Distance in kilometers


def text_match_score(text, query):
    """
    Calculate the score based on how well the text matches the query.
    The more words from the query appear in the text, the higher the score.
    """
    text = text.lower()
    query_words = query.lower().split()
    score = sum(1 for word in query_words if word in text)
    return score


# Helper functions for entity classification
def is_location(entity):
    """Simple check if entity might be a location"""
    # In a real implementation, use geocoding service or location database
    common_location_words = ['city', 'town', 'state', 'country', 'street']
    return any(word in entity for word in common_location_words)

def is_category(entity):
    """Check if entity might be a news category"""
    common_categories = [
        'technology', 'business', 'sports', 'entertainment', 
        'health', 'science', 'politics'
    ]
    return entity.lower() in common_categories

def is_news_source(entity):
    """Check if entity might be a news source"""
    common_sources = [
        'new york times', 'cnn', 'bbc', 'reuters', 
        'the guardian', 'wall street journal'
    ]
    return entity.lower() in common_sources

def geocode_address(address):
    """
    Converts a human-readable address to (latitude, longitude).
    Returns a tuple or None if it fails.
    """
    try:
        geolocator = Nominatim(user_agent="inshorts-news-bot-1589")
        location = geolocator.geocode(address)

        if location:
            return (location.latitude, location.longitude)
        else:
            return None

    except (GeocoderTimedOut, GeocoderServiceError) as e:
        print(f"Geocoding error: {e}")
        return None
