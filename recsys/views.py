from django.shortcuts import get_object_or_404, render
from django.views import generic
from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import F, Value, FilteredRelation, Q, Count
from django.db.models.functions import Lower
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator

from datetime import datetime
from itertools import chain
from functools import reduce

from .models import Books, More_Images, Contents, Translations, \
    Words, Rating, Isbns


class HomeView(generic.ListView):
    template_name = 'recsys/home.html'

    def get_queryset(self):
        num_books = 10
        highly_rated = Books.objects \
            .filter(isfdb_rating__gte=8).order_by('?')[:num_books//2]

        five_years_ago = datetime.now().year - 5
        recent_award_winners = Books.objects \
            .filter(year__gte=five_years_ago, 
                award_winner=True, juvenile=False) \
            .order_by('?')[:num_books//2]

        if not recent_award_winners:
            return highly_rated

        # return a queryset that alternates between the two catagories
        return [ b for b in 
            chain.from_iterable(zip(highly_rated, recent_award_winners)) ]


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
        contents = [ Books.objects.filter(pk=c.content_title_id)[0] 
                    for c in content_query_set]

        container_query_set = Contents.objects.filter(content_title_id=book.id)
        containers = [ Books.objects.filter(pk=c.book_title_id)[0] 
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
        search = self.request.GET.get('search').strip().lower()
        page_num = self.request.GET.get('page', 1)
        if request.user.is_authenticated:
            user = request.user
        else:
            user = None

        query = SearchQuery(
            search, config="isfdb_title_tsc", search_type='websearch')
        books = Books.objects.filter(**{'general_search': query}
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
            ).order_by('-exact_match', '-rank')


        if len(books) == 1:
            return book.get(self, request, books[0].id)
        elif len(books) == 0:
            possible_isbn = ''.join(filter(lambda x: x.isdigit(), search))
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

        paginator = Paginator(books, self.paginate_by)
        page_obj = paginator.page(page_num)

        if request.user.is_authenticated:
            book_ratings = []
            for b in page_obj.object_list:
                try:
                    rating = Rating.objects.get(book=b.id, user=request.user)
                except Rating.DoesNotExist:
                    rating = None
                book_ratings.append(rating)
        else:
            book_ratings = [None] * len(page_obj.object_list)

        template_data = dict(
            search=search,
            books_and_ratings=zip(page_obj.object_list, book_ratings),
            ratings=book_ratings,
            paginator=paginator,
            page_obj = paginator.get_page(page_num),
            is_paginated = len(books) > self.paginate_by,
        )

        rendered_page = render(request, "recsys/search_results.html", template_data)
        if rendered_page is not None:
            return rendered_page

class RatingsView(LoginRequiredMixin, generic.ListView):
    model = Books
    paginate_by = 10
    template_name = 'recsys/ratings.html'
    login_url = '/login/'
    redirect_field_name = 'redirect_to'

    def get_queryset(self):
        ratings = self.request.user.rating_set.order_by('-last_updated')
        return [r.book for r in ratings]
