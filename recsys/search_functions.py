
from django.contrib.postgres.search import SearchQuery, SearchRank

from django.db import connection
from django.db.models import F, Func, Value, FilteredRelation, Q, Case, \
    When, CharField, Avg
from django.db.models.functions import Lower
from django.contrib.postgres.aggregates import BoolAnd

CharField.register_lookup(Lower)

from .models import Books, Words, Isbns

# remove any character accent using the same method 
# used to unaccent the search terms in the general_search column
def unaccent(search):
    with connection.cursor() as cursor:
        cursor.execute("SELECT unaccent(%s)", [search])
        return cursor.fetchone()[0]


def select_bookrow_values(books):
    return books.values('title', 'year', 'authors', 'book_type', 
        'cover_image', 'pages', 'series_str_1', 'award_winner', 
        'juvenile', 'wikipedia', title_id=F('id'))


def general_book_search(search):
    query = SearchQuery(
        search, config="isfdb_title_tsc", search_type='websearch')
    books = Books.objects\
        .filter(
            general_search=query
        ).annotate(
            exact_match=Case(
                When(
                    title__lower=search, 
                    then=Value(1) + F('editions')
                ), 
                default=Value(0)
            )
        ).annotate(
            rank=SearchRank(
                F('general_search'), 
                query,
                normalization=Value(8),
                cover_density=True
            )
        )

    return select_bookrow_values(books) \
        .order_by('-exact_match', '-rank', 'title_id')

        

def joined_to_ratings(books, user_id):
    return books.annotate(
            rating_score=Avg('rating__rating', 
                filter=Q(rating__user = user_id)),
            rating_saved=BoolAnd('rating__saved', 
                filter=Q(rating__user = user_id)),
            rating_blocked=BoolAnd('rating__blocked', 
                filter=Q(rating__user = user_id)),
            rating_user=Value(user_id)
        )

