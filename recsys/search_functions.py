
from django.contrib.postgres.search import SearchQuery, SearchRank

from django.db import connection
from django.db.models import F, Value, FilteredRelation, Q

from .models import Books, Words, Isbns

# remove any character accent using the same method 
# used to unaccent the search terms in the general_search column
def unaccent(search):
    with connection.cursor() as cursor:
        cursor.execute("SELECT unaccent(%s)", [search])
        return cursor.fetchone()[0]


def general_book_search(search):
    query = SearchQuery(
        search, config="isfdb_title_tsc", search_type='websearch')
    return Books.objects\
        .filter(
        	general_search=query
        ).extra(
            select={'exact_match' : 'lower(title) = %s'},
            select_params=[search]
        ).annotate(
            rank=SearchRank(
                F('general_search'), 
                query,
                normalization=Value(8),
                cover_density=True
            )
        ).values('title', 'year', 'authors', 'book_type', 
            'cover_image', 'pages', 'series_str_1', 'award_winner', 
            'juvenile', 'wikipedia', title_id=F('id')) \
        .order_by('-exact_match', '-rank')

def joined_to_ratings(books, user_id):
	return books.annotate(
		    rating_score=F('rating__rating'), 
		    rating_saved=F('rating__saved'), 
		    rating_blocked=F('rating__blocked'), 
		    rating_user=F('rating__user')
		).filter(
		    Q(rating_user__isnull=True) | Q(rating_user=user_id) 
		)

