from django.http import JsonResponse
from .helpers import (
    call_groq_api,
    calculate_distance,
    generate_llm_summary,
    text_match_score,
    is_category,
    is_location,
    is_news_source
)
from InShorts_Project.models import Article
from django.shortcuts import render
from django.forms.models import model_to_dict
from django.db.models import Q

import logging

logger = logging.getLogger("InshortsProject")


def news_query_form(request):
    return render(request, "news_query_form.html")

def get_home_page(request):
    return render(request, "index.html")


def get_news_from_query(request):
    input_query = request.GET.get("query", "")
    #input_query = "Tell me latest development of ISRO and its chairman"
    print("FANGGGGGGGGGGGGG")

    if not input_query:
        return JsonResponse({"error": "No query provided"}, status=400)

    # Call Groq API to get structured information
    structured_data = call_groq_api(input_query)
    #structured_data = {"k": "b"}

    if structured_data:
        entities = structured_data.get("entities", [])
        intent = structured_data.get("intent", [])
        concepts = structured_data.get("concepts", [])

        # HARD CODING FOR TESTING
        #entities = ["ISRO","K Sivan"]
        #intent = ["source"]
        #concepts = ["space"] 

        # Fetch articles based on the intent extracted
        articles = fetch_articles_based_on_intent(request ,intent, entities, concepts)

        print(
            f"The llm generated data is {entities} and intent is {intent} and concept is {concepts}"
        )
        return JsonResponse({"articles": articles}, safe=False)
    else:
        return JsonResponse(
            {"error": "Error processing query with Groq API"}, status=500
        )

'''
def fetch_articles_based_on_intent(intent, entities, concepts):
    print("cooollllllllllllllllllll")
    articles = []

    # Example logic to fetch articles based on different intents
    if "nearby" in intent:
        # Handle geospatial query based on location (e.g., latitude, longitude)
        lat = entities[0].get("latitude", 0)
        lon = entities[0].get("longitude", 0)
        articles = Article.objects.filter(
            latitude__gte=lat - 0.1,
            latitude__lte=lat + 0.1,
            longitude__gte=lon - 0.1,
            longitude__lte=lon + 0.1,
        ).order_by("relevance_score")[:5]
    elif "source" in intent:
        articles = Article.objects.filter(
            source_name__in=[entity["value"] for entity in entities]
        ).order_by("-relevance_score")[:5]
    elif "category" in intent:
        articles = Article.objects.filter(category__contains=concepts).order_by(
            "-relevance_score"
        )[:5]

    # Enrich with LLM summaries
    for article in articles:
        article.llm_summary = generate_llm_summary(article.title, article.description)

    return list(articles)
'''
'''

def fetch_articles_based_on_intent(request,intent, entities, concepts):
    print("Intent-based fetch triggered")
    lat = float(request.GET.get("lat", 0))
    lon = float(request.GET.get("lon", 0))
    articles = []
    try:
      if "nearby" in intent:
          print("KKKK")
          articles = Article.objects.filter(
              latitude__gte=lat - 0.1,
              latitude__lte=lat + 0.1,
              longitude__gte=lon - 0.1,
              longitude__lte=lon + 0.1,
          )
          articles = sorted(
              articles, key=lambda x: calculate_distance(lat, lon, x.latitude, x.longitude)
          )[:5]

      elif "source" in intent:
          print("LLLL")
          source_names = [entity["value"] for entity in entities if "value" in entity]
          articles = Article.objects.filter(
              source_name__in=source_names
          ).order_by("-publication_date")[:5]

      elif "category" in intent:
          print("MMMM")
          if isinstance(concepts, list):
              articles = Article.objects.filter(
                  Q(category__icontains=concepts[0])  # optionally extend to include OR of all concepts
              ).order_by("-publication_date")[:5]
          else:
              articles = Article.objects.filter(
                  category__icontains=concepts
              ).order_by("-publication_date")[:5]

      # Convert to dicts and enrich with LLM summaries
      print("NNNN")
      articles_data = [model_to_dict(article) for article in articles]

      for idx, article_dict in enumerate(articles_data):
          article_dict.pop("id", None)
          print("OOOO")
          if idx == 0:
              article_dict["llm_summary"] = generate_llm_summary(
                  article_dict["title"], article_dict["description"], article_dict["url"]
              )
          else:
              article_dict["llm_summary"] = "PLACEHOLDER SUMMARY"
      print("PPPP")
      return articles_data
    except Exception as e:
        print("BUG IS ",e)
'''

def fetch_articles_based_on_intent(request, intent, entities, concepts):
    """
    Route the request to appropriate news fetching function based on intent and entities
    
    Args:
        request: Django request object
        intent: List of detected intents (e.g., ['category', 'source'])
        entities: List of extracted entities (e.g., ['New York Times', 'Technology'])
        concepts: List of extracted concepts (not currently used but available for future enhancements)
    
    Returns:
        JsonResponse with articles matching the intent and entities
    """
    # Convert to lowercase for case-insensitive matching
    intent = [i.lower() for i in intent]
    entities = [e.lower() for e in entities]
    
    # Determine primary intent (first in list or most specific)
    primary_intent = intent[0] if intent else 'trending'
    
    try:
        if 'nearby' in intent:
            # Look for location entities
            location_entity = next((e for e in entities if is_location(e)), None)
            if location_entity:
                # In a real implementation, you'd geocode the location to get lat/lon
                # For demo purposes, we'll use default coordinates
                request.GET = request.GET.copy()
                request.GET.update({'lat': 0, 'lon': 0})  # Replace with actual geocoding
                return get_news_nearby(request)
        
        if 'category' in intent:
            # Look for category in entities (e.g., "technology news")
            category_entity = next((e for e in entities if is_category(e)), None)
            if category_entity:
                request.GET = request.GET.copy()
                request.GET.update({'category': category_entity})
                return get_news_by_category(request)
        
        if 'source' in intent:
            # Look for news sources in entities
            source_entity = next((e for e in entities if is_news_source(e)), None)
            if source_entity:
                request.GET = request.GET.copy()
                request.GET.update({'source': source_entity})
                return get_news_by_source(request)
        
        if 'search' in intent or 'query' in intent:
            # Use all entities as search terms
            search_terms = " ".join(entities)
            if search_terms:
                request.GET = request.GET.copy()
                request.GET.update({'query': search_terms})
                return get_news_by_search(request)
        
        if 'trending' in intent:
            return get_trending_news(request)
        
        if 'score' in intent or 'relevance' in intent:
            request.GET = request.GET.copy()
            request.GET.update({'min_score': 0.7})  # Default threshold
            return get_news_by_score(request)
        
        # Default fallback to trending news
        return get_trending_news(request)
    
    except Exception as e:
        return JsonResponse(
            {"error": f"Failed to fetch articles: {str(e)}"}, 
            status=500
        )


def get_news_by_category(request):
    category = request.GET.get("category", "")
    category = "Technology"
    if not category:
        return JsonResponse({"error": "No category provided"}, status=400)

    # Fetch articles by category using Django ORM
    articles = Article.objects.filter(category__icontains=category).order_by(
        "-publication_date"
    )[:5]
    print(1)
    articles_data = [model_to_dict(article) for article in articles]
    print(2)
    count = 0
    for articles in articles_data:
        if count <= 5:
            llm_summary = generate_llm_summary(
                articles["title"], articles["description"], articles["url"]
            )
        else:
            llm_summary = "PLACEHOLDER SUMMARY"
        count += 1
        articles.pop("id")
        articles["llm_summary"] = llm_summary

    return JsonResponse({"articles": articles_data}, safe=False)


def get_news_by_score(request):
    min_score = float(request.GET.get("min_score", 0.7))

    articles = Article.objects.filter(relevance_score__gt=min_score).order_by(
        "-relevance_score"
    )[:5]

    articles_data = [model_to_dict(article) for article in articles]
    print(3333)
    count = 0
    for articles in articles_data:
        if count == 0:
            llm_summary = generate_llm_summary(
                articles["title"], articles["description"], articles["url"]
            )
        else:
            llm_summary = "PLACEHOLDER SUMMARY"
        count += 1
        articles.pop("id")
        articles["llm_summary"] = llm_summary

    return JsonResponse({"articles": articles_data}, safe=False)


def get_news_by_source(request):
    source = request.GET.get("source", "")
    if not source:
        return JsonResponse({"error": "No source provided"}, status=400)

    # Fetch articles by source
    articles = Article.objects.filter(source_name=source).order_by("-publication_date")[
        :5
    ]

    articles_data = [model_to_dict(article) for article in articles]
    print(44444444)
    count = 0
    for articles in articles_data:
        if count == 0:
            llm_summary = generate_llm_summary(
                articles["title"], articles["description"], articles["url"]
            )
        else:
            llm_summary = "PLACEHOLDER SUMMARY"
        count += 1
        articles.pop("id")
        articles["llm_summary"] = llm_summary

    return JsonResponse({"articles": articles_data}, safe=False)


def get_news_by_search(request):
    query = request.GET.get("query", "").strip()
    # query = "delhi" #test
    if not query:
        return JsonResponse({"error": "No search query provided"}, status=400)

    # Fetch a set of articles that contain the query in title or description, ordered by relevance_score
    candidate_articles = Article.objects.filter(
        Q(title__icontains=query) | Q(description__icontains=query)
    ).order_by("-relevance_score")[
        :50
    ]  # Fetch the top 50 articles
    print(2324343434)
    articles_data = [model_to_dict(article) for article in candidate_articles]
    ranked_articles = []

    # Calculate combined score (relevance_score + text match score)
    for article in articles_data:
        print(99)
        title_score = text_match_score(article["title"], query)
        desc_score = text_match_score(article["description"], query)
        match_score = title_score * 2 + desc_score  # Title match gets higher weight
        combined_score = (
            0.5 * article["relevance_score"] + 0.5 * match_score
        )  # Adjust weight as needed
        article["combined_score"] = combined_score

        ranked_articles.append(article)
    # Sort articles by combined score (highest score first)
    ranked_articles.sort(key=lambda x: x["combined_score"], reverse=True)
    ranked_articles = ranked_articles[:5]

    # Extract the top 5 ranked articles
    count = 0
    for articles in ranked_articles:
        if count == 0:
            llm_summary = generate_llm_summary(
                articles["title"], articles["description"], articles["url"]
            )
        else:
            llm_summary = "PLACEHOLDER SUMMARY"
        count += 1
        articles.pop("id")
        articles.pop("combined_score")
        articles["llm_summary"] = llm_summary

    return JsonResponse({"articles": ranked_articles}, safe=False)


def get_news_nearby(request):
    lat = float(request.GET.get("lat", 0))
    lon = float(request.GET.get("lon", 0))
    print(f"lat {lat} and lon are {lon}")

    articles = Article.objects.filter(
        latitude__gte=lat - 1.0,
        latitude__lte=lat + 1.0,
        longitude__gte=lon - 1.0,
        longitude__lte=lon + 1.0,
    )

    articles = sorted(
        articles, key=lambda x: calculate_distance(lat, lon, x.latitude, x.longitude)
    )[:5]

    articles_data = [model_to_dict(article) for article in articles]
    print(2)
    count = 0
    for articles in articles_data:
        if count == 0:
            llm_summary = generate_llm_summary(
                articles["title"], articles["description"], articles["url"]
            )
        else:
            llm_summary = "PLACEHOLDER SUMMARY"
        count += 1
        articles.pop("id")
        articles["llm_summary"] = llm_summary

    return JsonResponse({"articles": articles_data}, safe=False)


def get_trending_news(request):
    lat = float(request.GET.get("lat", 0))
    lon = float(request.GET.get("lon", 0))
    limit = int(request.GET.get("limit", 5))

    # Example logic for trending news (e.g., using interaction data, not implemented here)
    trending_articles = Article.objects.all().order_by("-relevance_score")[:limit]

    articles_data = [model_to_dict(article) for article in trending_articles]
    print(2)
    count = 0
    for articles in articles_data:
        if count == 0:
            llm_summary = generate_llm_summary(
                articles["title"], articles["description"], articles["url"]
            )
        else:
            llm_summary = "PLACEHOLDER SUMMARY"
        count += 1
        articles.pop("id")
        articles["llm_summary"] = llm_summary

    return JsonResponse({"articles": articles_data}, safe=False)