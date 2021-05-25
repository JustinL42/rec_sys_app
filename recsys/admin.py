from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import *

class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'authors')
    search_fields = ['title', 'authors']

class IsbnsAdmin(admin.ModelAdmin):
    list_display = ('isbn', 'title_id')
    search_fields = ['isbn', 'title_id']

class TranslationAdmin(admin.ModelAdmin):
    list_display = ('title', 'note')
    search_fields = ['title']

class ContentsAdmin(admin.ModelAdmin):
    list_display = ('book_title_id', 'content_title_id')
    search_fields = ['book_title_id', 'content_title_id']

class More_ImagesAdmin(admin.ModelAdmin):
    list_display = ('title_id', 'image')
    search_fields = ['title_id']

class WordsAdmin(admin.ModelAdmin):
    list_display = ('word', 'nentry', 'nentry_log')
    search_fields = ['word']

class CustomUserAdmin(UserAdmin):
    fieldsets = [f for f in UserAdmin.fieldsets ] + \
        [['Custom Fields', {'fields': ('virtual',)}]]

class BookClubAdmin(admin.ModelAdmin):
    fields = ('name', 'members', 'virtual')
    filter_horizontal = ('members',)

class MeetingAdmin(admin.ModelAdmin):
    list_display = ('book_club', 'book', 'date')

class RatingAdmin(admin.ModelAdmin):
    list_display = ('user', 'book', 'rating', 'saved', 'blocked')


class DataProblemAdmin(admin.ModelAdmin):
    list_display = ('book', 'user', 'problem')



admin.site.register(Books, BookAdmin)
admin.site.register(Isbns, IsbnsAdmin)
admin.site.register(Translations, TranslationAdmin)
admin.site.register(Contents, ContentsAdmin)
admin.site.register(More_Images, More_ImagesAdmin)
admin.site.register(Words, WordsAdmin)
admin.site.register(User, CustomUserAdmin)
admin.site.register(Book_Club, BookClubAdmin)
admin.site.register(Meeting, MeetingAdmin)
admin.site.register(Rating, RatingAdmin)
admin.site.register(DataProblem, DataProblemAdmin)


