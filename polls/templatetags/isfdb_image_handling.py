from django import template

register = template.Library()

@register.filter
def localize_isfdb_image_url(img_url):
    if not img_url:
        return "/static/polls/images/default_book_image.svg"
    elif "isfdb.org" in img_url:
        try:
            image_loc = img_url.split("/images/")[1]
            return "/static/polls/images/isfdb/" + image_loc
        except:
            return "/static/polls/images/default_book_image.svg"
    return img_url


@register.inclusion_tag('polls/book_row_item.html')
def book_row_item(book):
    return {'book': book}
