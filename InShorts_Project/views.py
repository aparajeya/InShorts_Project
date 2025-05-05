from django.http import JsonResponse
from .helpers import (
    call_groq_api,
    parse_news_query,
    calculate_distance,
    generate_llm_summary,
    text_match_score,
    geocode_address,
    select_top_articles,
)
from InShorts_Project.models import Article
from django.shortcuts import render
from django.forms.models import model_to_dict
from django.db.models import Q
import json

import logging

logger = logging.getLogger("InshortsProject")


def news_query_form(request):
    return render(request, "news_query_form.html")


def get_home_page(request):
    return render(request, "index.html")


def get_news_from_query(request):
    input_query = request.GET.get("query", "")

    if not input_query:
        return JsonResponse({"error": "No query provided"}, status=400)

    # Call Groq API to get structured information
    structured_data = parse_news_query(input_query)

    if structured_data:
        category = structured_data.get("category")
        score = structured_data.get("score")
        search = structured_data.get("search")
        source = structured_data.get("source")
        nearby = structured_data.get("nearby")
        all_articles = []

        if category:
            category_response = get_news_by_category(request)
            category_articles = json.loads(category_response.content).get(
                "articles", []
            )
            all_articles.append(category_articles)

        if source:
            source_response = get_news_by_source(request)
            source_articles = json.loads(source_response.content).get("articles", [])
            all_articles.append(source_articles)

        if search:
            request.GET._mutable = True
            request.GET["query"] = search
            search_response = get_news_by_search(request)
            search_articles = json.loads(search_response.content).get("articles", [])
            all_articles.append(search_articles)

        if nearby:
            coords = geocode_address(nearby)
            if coords:
                lat, lon = coords
                request.GET["lat"] = lat
                request.GET["lon"] = lon
                nearby_response = get_news_nearby(request)
                nearby_articles = json.loads(nearby_response.content).get(
                    "articles", []
                )
                all_articles.append(nearby_articles)

        if score:
            score_response = get_news_by_score(request)
            score_articles = json.loads(score_response.content).get("articles", [])
            all_articles.append(score_articles)

        articles = select_top_articles(all_articles, 5)
        return JsonResponse({"articles": articles}, safe=False)

    else:
        return JsonResponse(
            {"error": "Error processing query with Groq API"}, status=500
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

    articles_data = [model_to_dict(article) for article in articles]

    for articles in articles_data:
        llm_summary = generate_llm_summary(
            articles["title"], articles["description"], articles["url"]
        )
        articles.pop("id")
        articles["llm_summary"] = llm_summary

    return JsonResponse({"articles": articles_data}, safe=False)


def get_news_by_score(request):
    min_score = float(request.GET.get("min_score", 0.7))

    articles = Article.objects.filter(relevance_score__gt=min_score).order_by(
        "-relevance_score"
    )[:5]

    articles_data = [model_to_dict(article) for article in articles]

    for articles in articles_data:
        llm_summary = generate_llm_summary(
            articles["title"], articles["description"], articles["url"]
        )
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

    for articles in articles_data:
        llm_summary = generate_llm_summary(
            articles["title"], articles["description"], articles["url"]
        )
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
    articles_data = [model_to_dict(article) for article in candidate_articles]
    ranked_articles = []

    # Calculate combined score (relevance_score + text match score)
    for article in articles_data:
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

    for articles in ranked_articles:
        llm_summary = generate_llm_summary(
            articles["title"], articles["description"], articles["url"]
        )
        articles.pop("id")
        articles.pop("combined_score")
        articles["llm_summary"] = llm_summary

    return JsonResponse({"articles": ranked_articles}, safe=False)


def get_news_nearby(request):
    lat = float(request.GET.get("lat", 0))
    lon = float(request.GET.get("lon", 0))

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

    for articles in articles_data:
        llm_summary = generate_llm_summary(
            articles["title"], articles["description"], articles["url"]
        )
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

    for articles in articles_data:
        llm_summary = generate_llm_summary(
            articles["title"], articles["description"], articles["url"]
        )
        articles.pop("id")
        articles["llm_summary"] = llm_summary

    return JsonResponse({"articles": articles_data}, safe=False)
