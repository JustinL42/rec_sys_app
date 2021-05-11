from django.urls import path

from . import views

app_name = 'polls'
urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('<int:book_id>/', views.book, name='book'),
    path('search/', views.SearchResultsView.as_view(), name='search_results'),
]
