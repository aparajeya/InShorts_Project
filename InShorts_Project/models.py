from djongo import models


class Article(models.Model):
    id = models.CharField(max_length=100, primary_key=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    url = models.URLField()
    publication_date = models.DateTimeField()
    source_name = models.CharField(max_length=100)
    category = models.JSONField()  # Using JSONField to store a list of categories
    relevance_score = models.FloatField()
    latitude = models.FloatField()
    longitude = models.FloatField()

    class Meta:
        db_table = "articles"
        app_label = "InShorts_Project"
