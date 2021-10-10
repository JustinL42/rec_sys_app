from django.urls import path

from . import views

app_name = 'recsys'
urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('<int:book_id>/', views.book.as_view(), name='book'),
    path('search/', views.SearchResultsView.as_view(), name='search_results'),
    path('ratings/', views.RatingsView.as_view(), name='ratings'),
    path('recommendations/', views.RecommendationsView.as_view(), 
    	name='recommendations'),
	path('firstratings/', views.FirstRatingsView.as_view(), 
    	name='firstratings'),
    path('blocked/', views.BlockedView.as_view(), name='blocked'),
    path('saved/', views.SavedView.as_view(), name='saved'),

]
