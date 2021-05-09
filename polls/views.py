from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils import timezone
from django.views import generic
from django.contrib.postgres.search import \
    SearchQuery, SearchRank
from django.db.models import F, Value

from .models import Choice, Question, Books


class IndexView(generic.ListView):
    template_name = 'polls/index.html'
    context_object_name = 'tolkien_book_list'

    def get_queryset(self):
        return Books.objects.filter(
            authors="J. R. R. Tolkien"
        ).order_by('year')[:5]

# class IndexView(generic.ListView):
#     template_name = 'polls/index.html'
#     context_object_name = 'latest_question_list'

#     def get_queryset(self):
#         """
#         Return the last five published questions (not including those set to be
#         published in the future).
#         """
#         return Question.objects.filter(
#             pub_date__lte=timezone.now()
#         ).order_by('-pub_date')[:5]


def book(request, book_id):
    book = get_object_or_404(Books, id=book_id)

    if not book.cover_image:
        book.cover_image = "/static/polls/images/default_book_image.svg"
    elif "isfdb.org" in book.cover_image:
        try:
            image_loc = book.cover_image.split("/images/")[1]
            book.cover_image = "/static/polls/images/isfdb/" + image_loc
        except:
            book.cover_image = "/static/polls/images/default_book_image.svg"

    if not book.pages:
        book.pages = "Unknown number of"

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
        note=book.note

    )

    rendered_page = render(request, "polls/book.html", template_data)
    if rendered_page is not None:
        return rendered_page


class SearchResultsView(generic.ListView):
    model = Books
    template_name = 'polls/search_results.html'

    def get_queryset(self):
        search = self.request.GET.get('search')
        query = SearchQuery(search, config="isfdb_title_tsc")
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



class DetailView(generic.DetailView):
    model = Question
    template_name = 'polls/detail.html'

    def get_queryset(self):
        """
        Excludes any questions that aren't published yet.
        """
        return Question.objects.filter(pub_date__lte=timezone.now())


class ResultsView(generic.DetailView):
    model = Question
    template_name = 'polls/results.html'


def vote(request, question_id):
    question = get_object_or_404(Question, pk=question_id)
    try:
        selected_choice = question.choice_set.get(pk=request.POST['choice'])
    except (KeyError, Choice.DoesNotExist):
        return render(request, 'polls/detail.html', {
            'question': question,
            'error_message': "You didn't select a choice.",
        })
    else:
        selected_choice.votes += 1
        selected_choice.save()
        return HttpResponseRedirect(reverse('polls:results', args=(question.id,)))
