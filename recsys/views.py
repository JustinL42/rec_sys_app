from django.shortcuts import get_object_or_404, render
from django.views import generic
from django.contrib.postgres.search import SearchQuery, SearchRank
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import F, Value, FilteredRelation, Q
from django.core.paginator import Paginator

from datetime import datetime
from itertools import chain

from .models import Books, More_Images, Contents, Translations, \
    Words, Rating, Isbns

from .search_functions import unaccent, general_book_search, joined_to_ratings

class HomeView(generic.ListView):
    template_name = 'recsys/home.html'

    def get_queryset(self):
        num_books = 10
        highly_rated = Books.objects \
            .values('title', 'year', 'authors', 'book_type', 
                    'cover_image', 'pages', 'series_str_1', 'award_winner', 
                    'juvenile', 'wikipedia', title_id=F('id')) \
            .filter(isfdb_rating__gte=8).order_by('?')

        five_years_ago = datetime.now().year - 5
        recent_award_winners = Books.objects \
            .values('title', 'year', 'authors', 'book_type', 
                    'cover_image', 'pages', 'series_str_1', 'award_winner', 
                    'juvenile', 'wikipedia', title_id=F('id')) \
            .filter(year__gte=five_years_ago, 
                award_winner=True, juvenile=False) \
            .order_by('?')

        if self.request.user.is_authenticated:
            highly_rated = highly_rated.annotate(
                rating_score=F('rating__rating'), 
                rating_saved=F('rating__saved'), 
                rating_blocked=F('rating__blocked'), 
                rating_user=F('rating__user')
            ).filter(
                Q(rating_user__isnull=True) | 
                Q(rating_user=self.request.user.id) 
            )

            recent_award_winners = recent_award_winners.annotate(
                rating_score=F('rating__rating'), 
                rating_saved=F('rating__saved'), 
                rating_blocked=F('rating__blocked'), 
                rating_user=F('rating__user')
            ).filter(
                Q(rating_user__isnull=True) | 
                Q(rating_user=self.request.user.id) 
            )

        if not recent_award_winners:
            return highly_rated[:num_books]

        # return a queryset that alternates between the two catagories
        return [ b for b in 
            chain.from_iterable(zip(
                highly_rated[:num_books//2], 
                recent_award_winners[:num_books//2]
            )) ]


def isbn10_to_13(isbn10):
    cd = ( 10 - ( sum([38] + [int(x) * 3 for x in isbn10[:-1][0::2]] + \
        [int(x) for x in isbn10[:-1][1::2]]) % 10 ) ) % 10
    return '978' + isbn10[:-1]  + str(cd)

class book(generic.View):

    def post(self, request, book_id):
        error_text=None
        if not request.user.is_authenticated:
            error_text = "You must be logged in to rate books."
        else:
            try:
                new_rating = float(self.request.POST.get('new_rating'))
                if new_rating > 10 or new_rating < 1:
                    raise ValueError
            except (TypeError, ValueError):
                error_text = "The rating must be a whole number or " + \
                    "decimal between 1 and 10 (inclusive)."

        if not error_text:
            try:
                rating_obj = Rating.objects.get(
                    book=book_id, user=request.user.id)
            except Rating.DoesNotExist:
                b = Books.objects.get(pk=book_id)
                rating_obj = Rating(book=b, user=request.user)
            rating_obj.rating = new_rating
            rating_obj.save()

        return self.get(request, book_id, error_text=error_text)

    def get(self, request, book_id, error_text=None):
        book = get_object_or_404(Books, id=book_id)

        if request.user.is_authenticated:
            try:
                rating_obj = Rating.objects.get(
                    book=book_id, user=request.user.id)
                rating = rating_obj.rating
            except Rating.DoesNotExist:
                rating = None;
        else:
            rating = None    

        content_query_set = Contents.objects.filter(book_title_id=book.id)
        contents = [ Books.objects.filter(pk=c.content_title_id) \
            .values('title', 'year', 'authors', 'book_type', 'cover_image', 
                'pages', 'series_str_1', 'award_winner', 'juvenile', 
                'wikipedia', title_id=F('id') )[0]
                    for c in content_query_set]

        container_query_set = Contents.objects.filter(content_title_id=book.id) 
        containers = [ Books.objects.filter(pk=c.book_title_id) \
            .values('title', 'year', 'authors', 'book_type', 
                'cover_image', 'pages', 'series_str_1', 'award_winner', 
                'juvenile', 'wikipedia', title_id=F('id') )[0]
                    for c in container_query_set]

        if book.original_lang == "English":
            translations = []
        else:
            translations = Translations.objects \
            .filter(lowest_title_id=book.id) \
            .order_by('year')

        more_images = More_Images.objects.filter(title_id=book.id)

        template_data = dict(
            title_id=book_id,
            title=book.title,
            year=book.year,
            authors=book.authors,
            book_type=book.book_type,
            isbn=book.isbn,
            pages=book.pages,
            editions=book.editions,
            alt_titles=book.alt_titles,
            series_str_1 = book.series_str_1,
            series_str_2 = book.series_str_2,
            original_lang=book.original_lang,
            original_title=book.original_title,
            original_year=book.original_year,
            isfdb_rating=book.isfdb_rating,
            award_winner=book.award_winner,
            virtual = book.virtual,
            juvenile=book.juvenile,
            stand_alone=book.stand_alone,
            inconsistent=book.inconsistent,
            cover_image=book.cover_image,
            wikipedia=book.wikipedia,
            synopsis=book.synopsis,
            note=book.note,
            translations=translations,
            contents=contents,
            containers=containers,
            more_images=more_images,
            rating=rating,
            error_text=error_text
        )


        rendered_page = render(request, "recsys/book.html", template_data)
        if rendered_page is not None:
            return rendered_page


class SearchResultsView(generic.View):
    paginate_by = 10

    def get(self, request):
        search = unaccent(self.request.GET.get('search').strip().lower())
        page_num = self.request.GET.get('page', 1)
        search_errors = []

        books = general_book_search(search)
        if request.user.is_authenticated:
            books = joined_to_ratings(books, request.user.id)

        if len(books) == 1:
            return book.get(self, request, books[0]['title_id'])
        elif search == '':
            search_errors.append({'text': 'No search terms entered.'})
        elif len(books) == 0:

            possible_isbn = ''.join(filter(lambda x: x.isdigit(), search))
            if search[-1] in ['X', 'x']:
                possible_isbn += 'X'
            if len(possible_isbn) in [13, 10]:
                isbns_to_try = [possible_isbn]
                if len(possible_isbn) == 10:
                    isbns_to_try += [isbn10_to_13(possible_isbn)]
                for isbn in isbns_to_try:
                    try:
                        title_id = Isbns.objects.get(isbn=isbn).title_id
                        return book.get(self, request, title_id)
                    except Isbns.DoesNotExist:
                        pass

            new_search = []
            search_words = search.split()
            for i in range(len(search_words)):
                search_word = search_words[i]
                try:
                    # If this word is known to exist in the database, 
                    # try including it as-is in the new search
                    Words.objects.get(word=search_word)
                    new_search.append(search_word)
                    continue
                except Words.DoesNotExist:
                    pass

                # If the exact word isn't in the database, it may be a 
                # misspelling. Find 3 nearby words to suggest, and 
                # try the search again with the most popular word that 
                # is within 2 distance. 
                alt_word_query = Words.objects.raw("""
                    SELECT word, levenshtein(%s, word) AS distance
                    FROM recsys_words
                    WHERE levenshtein_less_equal(%s, word, 2) <= 2 
                    ORDER BY nentry_log DESC, distance
                    LIMIT 3;
                    """, (search_word,search_word))
                text = 'No results for "<b>{}</b>"'.format(search_word)
                alt_words = [w.word for w in alt_word_query]
                if not alt_words:
                    search_errors.append({'text': text })
                    continue
                new_search.append(alt_words[0])
                alt = []
                for alt_word in alt_words:
                    alt_search = "+".join(
                        search_words[:i] + [alt_word] + search_words[i+1:]
                    )
                    alt.append({'word': alt_word, 'search': alt_search})
                search_errors.append({'text': text, 'alt': alt })

            if new_search:
                new_search_str = ' '.join(new_search)
                text = 'Showing results for "<b>{}</b>"'.format(new_search_str)
                books = general_book_search(new_search_str)
                if request.user.is_authenticated:
                    books = joined_to_ratings(books, request.user.id)
                if len(books) == 1:
                    return book.get(self, request, books[0]['title_id'])
                elif len(books) == 0:
                    new_search_str = ' OR '.join(new_search)
                    books = general_book_search(new_search_str)
                    if request.user.is_authenticated:
                        books = joined_to_ratings(books, request.user.id)
                    search_errors.append({'text': 
                        "No book's data contains all the search terms."})
                    text = 'Showing results for "<b>{}</b>".'\
                        .format(new_search_str)
                search_errors.append({'text': text })

            if len(books) == 0:
                search_errors.append({'text': 'No results for this query.' })

        paginator = Paginator(books, self.paginate_by)
        page_obj = paginator.page(page_num)

        template_data = dict(
            search=search,
            books=page_obj.object_list,
            paginator=paginator,
            page_obj = paginator.get_page(page_num),
            is_paginated = len(books) > self.paginate_by,
            search_errors=search_errors
        )

        rendered_page = render(
            request, "recsys/search_results.html", template_data)
        if rendered_page is not None:
            return rendered_page

class RatingsView(LoginRequiredMixin, generic.ListView):
    model = Books
    paginate_by = 10
    template_name = 'recsys/ratings.html'
    login_url = '/login/'
    redirect_field_name = 'redirect_to'

    def get_queryset(self):
        return self.request.user.rating_set.select_related('book') \
        .values(
            title_id=F('book__id'), title=F('book__title'), 
            year=F('book__year'), authors=F('book__authors'), 
            book_type=F('book__book_type'), cover_image=F('book__cover_image'),
             pages=F('book__pages'), series_str_1=F('book__series_str_1'), 
             award_winner=F('book__award_winner'), 
             juvenile=F('book__juvenile'), wikipedi=F('book__wikipedia'), 
             rating_score=F('rating'), rating_saved=F('saved'), 
             rating_blocked=F('blocked'), rating_user=F('user') 
        ).order_by('-last_updated')
