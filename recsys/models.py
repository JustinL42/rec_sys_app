from django.db import models
from django.conf import settings
from django.contrib.postgres.search import SearchVectorField
from django.contrib.auth.models import AbstractUser
from django.utils import timezone

#       BOOK-RELATED MODELS

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

    contents_m2m = models.ManyToManyField(
        "self",
        through='Contents',
        through_fields=('book_title', 'content_title'),
        symmetrical=False,
        related_name='containers',
        related_query_name='container_title',
    )

    containers_m2m = models.ManyToManyField(
        "self",
        through='Contents',
        through_fields=('content_title', 'book_title'),
        symmetrical=False,
        related_name='contents',
        related_query_name='content_title',
    )

    options = {
        'managed' : False,
    }

    def __str__(self):
        return self.title


class Contents(models.Model):
    book_title = models.ForeignKey(
        Books, 
        null=False, 
        on_delete=models.CASCADE,
        related_name='c_contents',
    )
    content_title = models.ForeignKey(
        Books, 
        null=False, 
        on_delete=models.CASCADE,
        related_name='c_containers',
    )

    options = {
        'managed' : False,
    }

    def __str__(self):
        return "{}: {} contains {}".format(
            self.id, self.book_title, self.content_title
        )


class Isbns(models.Model):
    isbn = models.CharField(max_length=13)
    title = models.ForeignKey(
        Books, null=False,  db_constraint=False, on_delete=models.DO_NOTHING)

    options = {
        'managed' : False,
    }

    def __str__(self):
        return self.isbn


class Translations(models.Model):
    lowest_title = models.ForeignKey(
        Books, null=False,  db_constraint=False, on_delete=models.DO_NOTHING)
    title = models.CharField(max_length=5125)
    year = models.IntegerField()
    note = models.CharField(max_length=20000)

    options = {
        'managed' : False,
    }

    def __str__(self):
        return self.title


class More_Images(models.Model):
    title = models.ForeignKey(
        Books, null=False,  db_constraint=False, on_delete=models.DO_NOTHING)
    image = models.CharField(max_length=5125)

    options = {
        'managed' : False,
    }

    def __str__(self):
        return self.image


class Words(models.Model):
    word = models.CharField(primary_key=True, max_length=5125)
    ndoc = models.IntegerField(null=True)
    nentry = models.IntegerField(null=True)
    nentry_log = models.IntegerField(null=True)

    options = {
        'managed' : False,
    }

    def __str__(self):
        return self.word



#       USER-RELATED MODELS

class User(AbstractUser):
    location = models.CharField(max_length=250, null=True)
    age = models.IntegerField(null=True)
    virtual = models.BooleanField(null=False, default=False)    

    class Meta:
        indexes = [
            models.Index(fields=['username']),
            models.Index(fields=['first_name']),
        ]

    def __str__(self):
        return str(self.id) + ": " + self.first_name  + " " + self.last_name


class Book_Club(models.Model):
    name = models.CharField(max_length=256, null=True)
    members = models.ManyToManyField(
        User, 
        related_name="book_clubs",
        verbose_name="Members of the club"
    )
    virtual = models.BooleanField(null=False, default=False)
    virtual_member = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='virtual_member_of',
        null=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['name'], name='UniqueBookClubNames'
            )
        ]
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['virtual']),
        ]

    def __str__(self):
        return self.name

class Meeting(models.Model):
    book_club = models.ForeignKey(
        Book_Club, on_delete=models.CASCADE, null=False)
    book = models.ForeignKey(
        Books, on_delete=models.DO_NOTHING, null=True, db_constraint=False,)
    date = models.DateField(null=True)

    class Meta:
        indexes = [
            models.Index(fields=['book_club']),
            models.Index(fields=['book']),
            models.Index(fields=['date']),
        ]

    def __str__(self):
        return self.book.title + '(' + str(self.date) + ')'

class Rating(models.Model):
    book = models.ForeignKey(
        Books, null=False,  db_constraint=False, on_delete=models.DO_NOTHING)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=False, on_delete=models.CASCADE)
    rating = models.FloatField(null=True)
    predicted_rating = models.FloatField(null=True)
    original_rating = models.FloatField(null=True)
    original_min = models.FloatField(null=True)
    original_max = models.FloatField(null=True)
    saved = models.BooleanField(null=False, default=False)
    blocked = models.BooleanField(null=False, default=False)
    last_updated = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [
            models.Index(fields=['book']),
            models.Index(fields=['user']),
            models.Index(fields=['rating']),
            models.Index(models.Func('rating', function='FLOOR'), 
                name='floor_rating_idx'),
            models.Index(fields=['predicted_rating']),
            models.Index(models.Func('predicted_rating', function='FLOOR'), 
                name='floor_predicted_rating_idx'),
            models.Index(fields=['saved']),
            models.Index(fields=['blocked']),
            models.Index(fields=['last_updated'])
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['book', 'user'], name='OneRatingPerBookAndUser'
            ),
            models.CheckConstraint(check=models.Q(rating__gte=1), 
                name="RatingAtLeast1"
            ),
            models.CheckConstraint(check=models.Q(rating__lte=10), 
                name="RatingAtMost10"
            ),
            models.CheckConstraint(check=models.Q(original_rating__gte=models.F('original_min')), 
                name="OriginalRatingAtLeastMin"
            ),
            models.CheckConstraint(check=models.Q(original_rating__lte=models.F('original_max')), 
                name="OriginalRatingAtMostMax"
            ),
        ]



    def __str__(self):
        if self.rating != None:
            return self.user.first_name + " rates " + \
                str(self.rating) + " to " + self.book.title
        else:
            return self.user.first_name + " hasn't rated " + self.book.title

class DataProblem(models.Model):
    book = models.ForeignKey(
        Books, null=False, on_delete=models.DO_NOTHING, db_constraint=False,)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=False, on_delete=models.CASCADE)
    problem = models.CharField(max_length=32768)

    class Meta:
        indexes = [
            models.Index(fields=['book']),
            models.Index(fields=['user']),
        ]


    def __str__(self):
        return self.book.title