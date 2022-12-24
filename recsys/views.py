import os
import sys
from datetime import datetime
from itertools import chain

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.postgres.search import SearchQuery, SearchRank
from django.core.paginator import Paginator
from django.db.models import (
    CharField,
    Count,
    Exists,
    F,
    FilteredRelation,
    OuterRef,
    Q,
    Value,
)
from django.db.models.functions import MD5, Cast
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import generic

from .models import Books, Contents, Isbns, More_Images, Rating, Translations, Words
from .search_functions import (
    general_book_search,
    joined_to_ratings,
    select_bookrow_values,
    unaccent,
)

# add tuning package to path
path = os.path.join(os.path.dirname(__file__), os.pardir, "tuning")
sys.path.append(path)
from tune_update_methods import update_one_users_recs


class HomeView(generic.ListView):
    template_name = "recsys/home.html"

    def post(self, request):
        error_text = update_rating(request)
        return self.get(request, error_text=error_text)

    def get_queryset(self):
        num_books = 4
        highly_rated = (
            Books.objects.values(
                "title",
                "year",
                "authors",
                "book_type",
                "cover_image",
                "pages",
                "series_str_1",
                "award_winner",
                "juvenile",
                "wikipedia",
                title_id=F("id"),
            )
            .filter(isfdb_rating__gte=8)
            .order_by("?")
        )

        five_years_ago = datetime.now().year - 5
        recent_award_winners = (
            Books.objects.values(
                "title",
                "year",
                "authors",
                "book_type",
                "cover_image",
                "pages",
                "series_str_1",
                "award_winner",
                "juvenile",
                "wikipedia",
                title_id=F("id"),
            )
            .filter(
                year__gte=five_years_ago, award_winner=True, juvenile=False
            )
            .order_by("?")
        )

        if self.request.user.is_authenticated:
            highly_rated = highly_rated.annotate(
                rating_score=F("rating__rating"),
                rating_saved=F("rating__saved"),
                rating_blocked=F("rating__blocked"),
                rating_user=F("rating__user"),
            ).filter(
                Q(rating_user__isnull=True)
                | Q(rating_user=self.request.user.id)
            )

            recent_award_winners = recent_award_winners.annotate(
                rating_score=F("rating__rating"),
                rating_saved=F("rating__saved"),
                rating_blocked=F("rating__blocked"),
                rating_user=F("rating__user"),
            ).filter(
                Q(rating_user__isnull=True)
                | Q(rating_user=self.request.user.id)
            )

        if not recent_award_winners:
            return highly_rated[:num_books]

        # return a queryset that alternates between the two catagories
        return [
            b
            for b in chain.from_iterable(
                zip(
                    highly_rated[: num_books // 2],
                    recent_award_winners[: num_books // 2],
                )
            )
        ]


def isbn10_to_13(isbn10):
    cd = (
        10
        - (
            sum(
                [38]
                + [int(x) * 3 for x in isbn10[:-1][0::2]]
                + [int(x) for x in isbn10[:-1][1::2]]
            )
            % 10
        )
    ) % 10
    return "978" + isbn10[:-1] + str(cd)


class book(generic.View):
    def post(self, request, book_id):
        error_text = update_rating(request)
        return self.get(request, book_id, error_text=error_text)

    def get(self, request, book_id, error_text=None):
        book = get_object_or_404(Books, id=book_id)

        if request.user.is_authenticated:
            try:
                rating_obj = Rating.objects.get(
                    book=book_id, user=request.user.id
                )
                rating = rating_obj.rating
                saved = rating_obj.saved
                blocked = rating_obj.blocked
            except Rating.DoesNotExist:
                rating = saved = blocked = None
        else:
            rating = saved = blocked = None

        translations = book.translations_set.all().order_by("year")
        more_images = book.more_images_set.all()

        contents = select_bookrow_values(book.contents.all()).order_by("year")
        containers = select_bookrow_values(book.containers.all()).order_by(
            "year"
        )

        if request.user.is_authenticated:
            contents = joined_to_ratings(contents, request.user.id)
            containers = joined_to_ratings(containers, request.user.id)

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
            series_str_1=book.series_str_1,
            series_str_2=book.series_str_2,
            original_lang=book.original_lang,
            original_title=book.original_title,
            original_year=book.original_year,
            isfdb_rating=book.isfdb_rating,
            award_winner=book.award_winner,
            virtual=book.virtual,
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
            rating_saved=saved,
            rating_blocked=blocked,
            error_text=error_text,
        )

        rendered_page = render(request, "recsys/book.html", template_data)
        if rendered_page is not None:
            return rendered_page


class SearchResultsView(generic.View):
    paginate_by = 8

    def post(self, request):
        error_text = update_rating(request)
        return self.get(request, error_text=error_text)

    def get(self, request, error_text=None):
        search = unaccent(self.request.GET.get("search").strip().lower())
        search_errors = []
        if len(search) > 70:
            search_errors.append(
                {"text": "The character limit for the search string is 70."}
            )
            return render(
                request,
                "recsys/search_results.html",
                {"search_errors": search_errors},
            )

        page_num = self.request.GET.get("page", 1)

        books = general_book_search(search)

        if request.user.is_authenticated and books:
            books = joined_to_ratings(books, request.user.id)

        if len(books) == 1:
            return book.get(self, request, books[0]["title_id"])
        elif search == "" or search == None:
            search_errors.append({"text": "No search terms entered."})
        elif len(books) == 0:

            possible_isbn = "".join(filter(lambda x: x.isdigit(), search))
            if search[-1] in ["X", "x"]:
                possible_isbn += "X"
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
                alt_word_query = Words.objects.raw(
                    """
                    SELECT word, levenshtein(%s, word) AS distance
                    FROM recsys_words
                    WHERE levenshtein_less_equal(%s, word, 2) <= 2 
                    ORDER BY nentry_log DESC, distance
                    LIMIT 3;
                    """,
                    (search_word, search_word),
                )
                text = 'No results for "<b>{}</b>"'.format(search_word)
                alt_words = [w.word for w in alt_word_query]
                if not alt_words:
                    search_errors.append({"text": text})
                    continue
                new_search.append(alt_words[0])
                alt = []
                for alt_word in alt_words:
                    alt_search = "+".join(
                        search_words[:i] + [alt_word] + search_words[i + 1 :]
                    )
                    alt.append({"word": alt_word, "search": alt_search})
                search_errors.append({"text": text, "alt": alt})

            if new_search:
                new_search_str = " ".join(new_search)
                text = 'Showing results for "<b>{}</b>"'.format(new_search_str)
                books = general_book_search(new_search_str)
                if request.user.is_authenticated:
                    books = joined_to_ratings(books, request.user.id)
                if len(books) == 1:
                    return book.get(self, request, books[0]["title_id"])
                elif len(books) == 0:
                    new_search_str = " OR ".join(new_search)
                    books = general_book_search(new_search_str)
                    if request.user.is_authenticated:
                        books = joined_to_ratings(books, request.user.id)
                    search_errors.append(
                        {
                            "text": "No book's data contains all the search terms."
                        }
                    )
                    text = 'Showing results for "<b>{}</b>".'.format(
                        new_search_str
                    )
                search_errors.append({"text": text})

            if len(books) == 0:
                search_errors.append({"text": "No results for this query."})

        paginator = Paginator(books, self.paginate_by)
        page_obj = paginator.page(page_num)

        template_data = dict(
            search=search,
            books=page_obj.object_list,
            paginator=paginator,
            page_obj=paginator.get_page(page_num),
            is_paginated=len(books) > self.paginate_by,
            search_errors=search_errors,
            error_text=error_text,
        )

        rendered_page = render(
            request, "recsys/search_results.html", template_data
        )
        if rendered_page is not None:
            return rendered_page


class AbstractRatingsView(LoginRequiredMixin, generic.ListView):
    model = Books
    paginate_by = 20
    login_url = "/login/"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["in_ratings_tab"] = True
        context["rating_count"] = (
            self.request.user.rating_set.select_related("book")
            .filter(rating__isnull=False)
            .count()
        )
        context["saved_count"] = (
            self.request.user.rating_set.select_related("book")
            .filter(saved=True)
            .count()
        )
        context["blocked_count"] = (
            self.request.user.rating_set.select_related("book")
            .filter(blocked=True)
            .count()
        )
        return context

    def post(self, request):
        error_text = update_rating(request)
        return self.get(request, error_text=error_text)


class RatingsView(AbstractRatingsView):
    template_name = "recsys/ratings.html"

    def get_queryset(self):
        ratings = self.request.user.rating_set.select_related("book").filter(
            rating__isnull=False
        )
        return select_ratings_row_values(ratings).order_by(
            "-last_updated", "-year", "id"
        )


class SavedView(AbstractRatingsView):
    template_name = "recsys/saved.html"

    def get_queryset(self):
        ratings = self.request.user.rating_set.select_related("book").filter(
            saved=True
        )
        return select_ratings_row_values(ratings).order_by("-last_updated")


class BlockedView(AbstractRatingsView):
    template_name = "recsys/blocked.html"

    def get_queryset(self):
        ratings = self.request.user.rating_set.select_related("book").filter(
            blocked=True
        )
        return select_ratings_row_values(ratings).order_by("-last_updated")


class RecommendationsView(LoginRequiredMixin, generic.ListView):
    template_name = "recsys/recommendations.html"
    model = Books
    paginate_by = 10
    login_url = "/login/"

    def post(self, request):
        error_text = update_rating(request)
        return self.get(request, error_text=error_text)

    def get_queryset(self):
        recs = self.request.user.rating_set.select_related("book").filter(
            predicted_rating__isnull=False,
            rating__isnull=True,
            saved=False,
            blocked=False,
        )
        return select_ratings_row_values(recs).order_by(
            "-predicted_rating", "-year", "id"
        )


class FirstRatingsView(LoginRequiredMixin, generic.View):
    login_url = "/login/"
    paginate_by = 8
    book_limit = 160

    # The first cold-start page shows a selection of popular books
    # in the order predetermined by the cold_start_rank, which was set
    # during the database migration. It includes both highly awarded
    # novels and the most commonly viewed novels on isfd.org. Filter out
    # books that don't already have two ratings, since this will be
    # unhelpful in generating recommendations.
    def get(self, request, error_text=None):
        page_num = self.request.GET.get("page", 1)
        books = (
            Books.objects.filter(cold_start_rank__isnull=False)
            .annotate(
                multiple_ratings_exist=Exists(
                    Rating.objects.filter(rating__isnull=False)
                    .values("book_id")
                    .annotate(num_ratings=Count("book_id"))
                    .filter(num_ratings__gt=1)
                    .filter(book_id=OuterRef("id"))
                )
            )
            .filter(multiple_ratings_exist=True)
            .order_by("cold_start_rank", "id")[: self.book_limit]
        )
        books = joined_to_ratings(
            select_bookrow_values(books), request.user.id
        )

        paginator = Paginator(books, self.paginate_by)
        page_obj = paginator.page(page_num)
        rating_count = (
            self.request.user.rating_set.select_related("book")
            .filter(rating__isnull=False)
            .count()
        )

        template_data = dict(
            books=page_obj.object_list,
            paginator=paginator,
            page_obj=paginator.get_page(page_num),
            is_paginated=len(books) > self.paginate_by,
            error_text=error_text,
            rating_count=rating_count,
        )

        return render(request, "recsys/firstratings.html", template_data)

    def post(self, request):
        if "done" not in request.POST:
            error_text = update_rating(request)
            return self.get(request, error_text=error_text)
        else:
            # Get both the top 12 and bottom 12 recommendations. This will
            # give the user opportunities to give both high and low ratings,
            # and will may help correct the model's most extreme guesses
            # about the user's taste.
            update_one_users_recs(
                request.user.id,
                top_n=12,
                bottom_n=12,
                urgent=True,
                cold_start=True,
            )
            return redirect("/secondratings/")


class SecondRatingsView(LoginRequiredMixin, generic.ListView):
    model = Books
    paginate_by = 8
    login_url = "/login/"
    template_name = "recsys/secondratings.html"
    book_limit = 20
    initial_rec_limit = 120

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["rating_count"] = (
            self.request.user.rating_set.select_related("book")
            .filter(rating__isnull=False)
            .count()
        )
        return context

    # The books need to be sorted in an immutable order so they don't
    # get shuffled when the user gives a rating and the page is reloaded.
    # However, it should also be pseudo-random to avoid grouping high-rated
    # or low-rated books, or sorting by age or another factor.
    # For this reason, the MD5 checksum of the book id is used.
    def get_queryset(self):
        ratings = (
            self.request.user.rating_set.select_related("book")
            .filter(
                book__cold_start_rank__isnull=False,
                predicted_rating__isnull=False,
                rating__isnull=True,
                blocked=False,
            )
            .annotate(
                #
                sort_val=MD5(Cast("book__id", output_field=CharField()))
            )
        )
        return select_ratings_row_values(ratings).order_by("sort_val")[
            : self.book_limit
        ]

    def post(self, request):
        if "done" not in request.POST:
            error_text = update_rating(request)
            return self.get(request, error_text=error_text)
        else:
            # The final cold start recommendations are limited to 120 simply
            # because database inserts are one of the more time-consuming parts
            # of the method and the page needs to be returned fast.
            update_one_users_recs(
                request.user.id,
                top_n=self.initial_rec_limit,
                urgent=True,
                cold_start=True,
            )
            return redirect("/recommendations/")


def select_ratings_row_values(ratings):
    return ratings.values(
        title_id=F("book__id"),
        title=F("book__title"),
        year=F("book__year"),
        authors=F("book__authors"),
        book_type=F("book__book_type"),
        cover_image=F("book__cover_image"),
        pages=F("book__pages"),
        series_str_1=F("book__series_str_1"),
        award_winner=F("book__award_winner"),
        juvenile=F("book__juvenile"),
        wikipedi=F("book__wikipedia"),
        rating_score=F("rating"),
        rating_saved=F("saved"),
        rating_blocked=F("blocked"),
        rating_user=F("user"),
        cold_start_rank=F("book__cold_start_rank"),
    )


def update_rating(request):
    error_text = None
    new_rating = request.POST.get("new_rating")
    rating_title_id = request.POST.get("rating_title_id")
    save = bool(request.POST.get("save"))
    block = bool(request.POST.get("block"))

    if not request.user.is_authenticated:
        error_text = "You must be logged in to rate books."
    elif new_rating == "":
        new_rating = None
    else:
        try:
            new_rating = float(new_rating)
            if new_rating > 10 or new_rating < 1:
                raise ValueError
        except (TypeError, ValueError):
            error_text = (
                "The rating must be a whole number or "
                + "decimal between 1 and 10 (inclusive)."
            )

    if not error_text:
        try:
            rating_obj = Rating.objects.get(
                book=rating_title_id, user=request.user.id
            )
        except Rating.DoesNotExist:
            b = Books.objects.get(pk=rating_title_id)
            rating_obj = Rating(book=b, user=request.user)
        rating_obj.rating = new_rating
        rating_obj.saved = save
        rating_obj.blocked = block
        rating_obj.last_updated = timezone.now()
        rating_obj.save()

    return error_text
