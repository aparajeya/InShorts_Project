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

#TODO move this to .env file
GROQ_API_KEY = "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"
url = "https://api.groq.com/openai/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {GROQ_API_KEY}",
    "Content-Type": "application/json",
}


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

            """
            Response Structure = {'entities': [{'type': 'person', 'name': 'Indian PM'}, {'type': 'location', 'name': 'US'}], 'intent': ['nearby', 'source'], 'concepts': ['politics']}
            """
            return json.loads(json_str)
        except Exception as e:
            raise e
    else:
        return None


def parse_news_query(input_query):
    system_prompt = """
    You are a news query processor. Your task is to convert user queries into structured data used by a news retrieval system.

    For each query, populate the following fields:
    1. "category": Return relevant categories like politics, sports, technology, business, etc. You can return multiple.
    2. "score": Leave this blank always.
    3. "search": Extract **one essential keyword** from the query that best represents the search intent.
    4. "source": Extract only if the user mentions a specific source (e.g., BBC, CNN). Else, return empty.
    5. "nearby": Extract the location if user is asking for news from or near a place (e.g., in Delhi, near Mumbai).

    Only return the result in this exact JSON format:
    {
      "category": [...],
      "score": "",
      "search": "...",
      "source": "...",
      "nearby": "..."
    }
    Do NOT include any explanations or text outside the JSON.
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
            json_str = re.search(r"\{.*\}", reply, re.DOTALL).group(0)
            return json.loads(json_str)
        except Exception as e:
            raise e
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
        return None


def select_top_articles(article_lists, max_articles=5):
    """
    Selects up to `max_articles` from the given list of article lists.
    It picks one article from each list in round-robin fashion.

    Args:
        article_lists (List[List[dict]]): A list containing multiple article lists.
        max_articles (int): Maximum number of articles to return.

    Returns:
        List[dict]: Combined list of up to `max_articles` articles.
    """
    final_articles = []
    index = 0

    while len(final_articles) < max_articles:
        added_any = False

        for articles in article_lists:
            if index < len(articles):
                final_articles.append(articles[index])
                added_any = True

            if len(final_articles) == max_articles:
                break

        if not added_any:
            break

        index += 1

    return final_articles
