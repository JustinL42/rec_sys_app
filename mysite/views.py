from django.contrib.auth.forms import ValidationError
from django.urls import reverse_lazy
from django.views.generic import View
from django.shortcuts import render
from django.contrib.auth.models import User
from django.contrib.auth.mixins import LoginRequiredMixin


class UserNameChangeView(LoginRequiredMixin, View):

    def get(self, request):
        return render(request, "registration/username_change.html")

    def post(self, request):
        old_username=request.user.username
        new_username = self.request.POST.get('new_username')

        if new_username == old_username:
            error_text = \
            u'Your user name already is "{}". Choose a different name'\
            .format(new_username)
            return render(request, "registration/username_change.html", 
                {'error_text': error_text } )

        if User.objects.filter(username=new_username).exists():
            error_text = u'Username "{}" is not available.'.format(new_username)
            return render(request, "registration/username_change.html", 
                {'error_text': error_text } )

        user = User.objects.get(username = old_username)
        user.username = new_username
        user.save()
        return render(request, "registration/username_change_done.html",
            { 'new_username' : new_username} )


class AccountDeleteView(LoginRequiredMixin, View):

    def get(self, request):
        return render(request, "registration/account_delete.html")

    def post(self, request):
        username = request.user.username
        typed_username = self.request.POST.get('username')
        if typed_username != username:
            error_text = \
            u'Your user name isn\'t "<b>{}</b>". You must type your ' +\
            u'user name exactly in order to delete your account.'
            error_text = error_text.format(typed_username)
            return render(request, "registration/account_delete.html", 
                {'error_text': error_text } )

        user = User.objects.get(username = username)
        user.delete()
        return render(request, "registration/account_delete_done.html",
            { 'deleted_user' : username} )