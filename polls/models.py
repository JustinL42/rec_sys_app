import datetime

from django.db import models
from django.utils import timezone
from django.contrib.postgres.search import SearchVectorField


class Books(models.Model):
    title = models.CharField(max_length=5125)
    year = models.IntegerField()
    authors = models.CharField(max_length=5125, null=True)
    book_type = models.CharField(max_length=13)
    isbn = models.CharField(max_length=13, null=True)
    pages = models.IntegerField()
    editions = models.IntegerField()
    alt_titles = models.CharField(max_length=5125, null=True)
    series_str_1 = models.CharField(max_length=5125, null=True)
    series_str_2 = models.CharField(max_length=5125, null=True)
    original_lang = models.CharField(max_length=40)
    original_title = models.CharField(max_length=5125, null=True)
    original_year = models.IntegerField()
    isfdb_rating = models.FloatField()
    award_winner = models.BooleanField()
    juvenile = models.BooleanField()
    stand_alone = models.BooleanField()
    inconsistent = models.BooleanField()
    virtual = models.BooleanField()
    cover_image = models.CharField(max_length=5125, null=True)
    wikipedia = models.CharField(max_length=20000, null=True)
    synopsis = models.CharField(max_length=20000, null=True)
    note = models.CharField(max_length=5125, null=True)
    general_search = SearchVectorField(null=True)

    def __str__(self):
        return self.title


class Isbns(models.Model):
    isbn = models.CharField(max_length=13)
    title_id = models.IntegerField()

    def __str__(self):
        return self.isbn


class Translations(models.Model):
    newest_title_id = models.IntegerField()
    title = models.CharField(max_length=5125)
    year = models.IntegerField()
    note = models.CharField(max_length=20000)

    def __str__(self):
        return self.title


class Contents(models.Model):
    book_title_id = models.IntegerField()
    content_title_id = models.IntegerField()

    def __str__(self):
        return str(self.book_title_id)

class More_Images(models.Model):
    title_id = models.IntegerField()
    image = models.CharField(max_length=5125)

    def __str__(self):
        return self.image

class Words(models.Model):
    word = models.CharField(primary_key=True, max_length=5125)

    def __str__(self):
        return self.word



class Question(models.Model):
    question_text = models.CharField(max_length=200)
    pub_date = models.DateTimeField('date published')

    def __str__(self):
        return self.question_text

    def was_published_recently(self):
        now = timezone.now()
        return now - datetime.timedelta(days=1) <= self.pub_date <= now
    
    was_published_recently.admin_order_field = 'pub_date'
    was_published_recently.boolean = True
    was_published_recently.short_description = 'Published recently?'


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    choice_text = models.CharField(max_length=200)
    votes = models.IntegerField(default=0)

    def __str__(self):
        return self.choice_text
