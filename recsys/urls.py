from django.urls import path

from . import views

app_name = 'recsys'
urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('<int:book_id>/', views.book.as_view(), name='book'),
    path('search/', views.SearchResultsView.as_view(), name='search_results'),
    path('ratings/', views.RatingsView.as_view(), name='ratings'),
]