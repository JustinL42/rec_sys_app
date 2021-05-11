from django.shortcuts import get_object_or_404, render
from django.views import generic
from django.contrib.postgres.search import SearchQuery, SearchRank
from django.db.models import F, Value

from .models import Books, More_Images, Contents, Translations, Words


class HomeView(generic.ListView):
    template_name = 'polls/home.html'
    context_object_name = 'tolkien_book_list'

    def get_queryset(self):
        return Books.objects.filter(
            authors="J. R. R. Tolkien"
        ).order_by('year')[:5]


def book(request, book_id):
    book = get_object_or_404(Books, id=book_id)
    

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
        .filter(newest_title_id=book.id) \
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
        more_images=more_images
    )


    rendered_page = render(request, "polls/book.html", template_data)
    if rendered_page is not None:
        return rendered_page


class SearchResultsView(generic.ListView):
    model = Books
    template_name = 'polls/search_results.html'

    def get_queryset(self):
        search = self.request.GET.get('search')
        query = SearchQuery(
            search, config="isfdb_title_tsc", search_type='websearch')
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
