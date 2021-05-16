from django.shortcuts import get_object_or_404, render
from django.views import generic
from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import F, Value
from django.contrib.auth.mixins import LoginRequiredMixin


from .models import Books, More_Images, Contents, Translations, Words, Rating


class HomeView(generic.ListView):
    template_name = 'recsys/home.html'
    context_object_name = 'tolkien_book_list'

    def get_queryset(self):
        return Books.objects.filter(
            authors="J. R. R. Tolkien"
        ).order_by('year')[:5]


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


class SearchResultsView(generic.ListView):
    model = Books
    template_name = 'recsys/search_results.html'

    def get_queryset(self):
        search = self.request.GET.get('search')
        query = SearchQuery(
            search, config="isfdb_title_tsc", search_type='websearch')
        print(query)
        return (
            Books.objects.filter(**{'general_search': query})
            .annotate(rank=SearchRank(
                F('general_search'), 
                query,
                normalization=Value(8),
                cover_density=True
            )
            ).order_by("-rank")

        ) 

class RatingsView(LoginRequiredMixin, generic.ListView):
    model = Books
    template_name = 'recsys/ratings.html'

    def get_queryset(self):
        ratings = self.request.user.rating_set.order_by('-last_updated')
        return [r.book for r in ratings]
