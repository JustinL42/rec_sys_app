from django.urls import path, re_path

from . import views

app_name = "recsys"
urlpatterns = [
    path("", views.HomeView.as_view(), name="home"),
    path("<int:book_id>/", views.book.as_view(), name="book"),
    path("search/", views.SearchResultsView.as_view(), name="search_results"),
    path("ratings/", views.RatingsView.as_view(), name="ratings"),
    path(
        "recommendations/",
        views.RecommendationsView.as_view(),
        name="recommendations",
    ),
    path(
        "firstratings/", views.FirstRatingsView.as_view(), name="firstratings"
    ),
    path(
        "secondratings/",
        views.SecondRatingsView.as_view(),
        name="secondratings",
    ),
    path("blocked/", views.BlockedView.as_view(), name="blocked"),
    path("saved/", views.SavedView.as_view(), name="saved"),
    re_path(r"^blog/$", views.BlogView.as_view(), name="blog"),
    path(
        "blog/<str:post_name>/",
        views.BlogPostView.as_view(),
        name="blog_post"
    ),
    path("about/", views.AboutView.as_view(), name="about"),
]
