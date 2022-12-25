from django import template

register = template.Library()


@register.filter
def localize_isfdb_image_url(img_url):
    if not img_url:
        return "/static/recsys/images/default_book_image.svg"
    elif "isfdb.org" in img_url:
        try:
            image_loc = img_url.split("/images/")[1]
            return "/static/recsys/images/isfdb/" + image_loc
        except IndexError:
            return "/static/recsys/images/default_book_image.svg"
    return img_url


@register.inclusion_tag("recsys/book_row_item.html", takes_context=True)
def book_row_item(context, book):
    return {"book": book, "user": context["user"]}
