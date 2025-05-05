"""
URL configuration for InShorts_Project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path
from .views import (
    get_news_from_query,
    get_news_by_category,
    get_news_by_score,
    get_news_by_source,
    get_news_nearby,
    get_trending_news,
    news_query_form,
    get_news_by_search,
    get_home_page,
)


urlpatterns = [
    path("admin/", admin.site.urls),
    path("", get_home_page, name="get_home_page"),
    path("get-news/query/", get_news_from_query, name="get_news_from_query"),
    path("get-news/category/", get_news_by_category, name="get_news_by_category"),
    path("get-news/score/", get_news_by_score, name="get_news_by_score"),
    path("get-news/source/", get_news_by_source, name="get_news_by_source"),
    path("get-news/nearby/", get_news_nearby, name="get_news_nearby"),
    path("get-news/trending/", get_trending_news, name="get_trending_news"),
    path("get-news/search/", get_news_by_search, name="get_news_by_search"),
    path("news-query/", news_query_form, name="news_query_form"),
    path("news", news_query_form, name="home"),
]
