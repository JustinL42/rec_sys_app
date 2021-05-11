from django.contrib import admin

from .models import Books, Isbns, Translations, Contents, More_Images, Words

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
    list_display = ('word', )
    search_fields = ['word']

admin.site.register(Books, BookAdmin)
admin.site.register(Isbns, IsbnsAdmin)
admin.site.register(Translations, TranslationAdmin)
admin.site.register(Contents, ContentsAdmin)
admin.site.register(More_Images, More_ImagesAdmin)
admin.site.register(Words, WordsAdmin)
