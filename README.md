Overview
The News Retrieval System is a web application designed to fetch and display news articles based on various user queries. It allows users to retrieve articles based on different intents such as category, relevance score, source, search query, and proximity to a specified location. The application presents news articles in a card-based format with details such as title, summary, publication date, and source.

The backend is built using Django, while the frontend is built with HTML, CSS, and JavaScript.

Features
News Intent Selection: Users can choose the intent for fetching news:

Custom Queries: Use Groq API to process user queries and extract relevant intent. The system then selects the appropriate data retrieval strategy to fetch results based on the user's query.

Category: Retrieve articles from a specified category (e.g., Technology, Business).

Score: Fetch articles based on a minimum relevance score.

Search: Search articles by a specific query (e.g., "Elon Musk").

Source: Retrieve news articles from specific sources (e.g., New York Times).

Nearby: Get articles related to a specific geographic location.

An LLM Summary is added to each article using Groq API which can be seen on the frontend.

