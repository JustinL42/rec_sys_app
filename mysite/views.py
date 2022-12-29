import re

from django.contrib.auth import authenticate, get_user_model, login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.password_validation import validate_password
from django.core.validators import ValidationError, validate_email
from django.shortcuts import redirect, render
from django.views.generic import View
from django.views.generic.base import TemplateView

User = get_user_model()


class AbstractAccount(TemplateView):
    login_url = "/login/"
    redirect_field_name = "redirect_to"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["in_account_tab"] = True
        return context


class Account(LoginRequiredMixin, AbstractAccount):
    template_name = "registration/account.html"


class SignUpView(View):
    def get(self, request, context=None):
        return render(request, "registration/signup.html", context)

    def post(self, request, context):
        username = request.POST.get("username")
        displayname = request.POST.get("displayname").strip()
        email = request.POST.get("email").strip()
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")

        if not all([username, displayname, email, password1, password2]):

            error_text = "\nMissing a required field."
            return render(
                request,
                "registration/signup.html",
                {
                    "error_list": [error_text],
                    "username": username,
                    "displayname": displayname,
                    "email": email,
                },
            )

        error_list = []

        if len(username) > 60:
            error_list.append("Username must be 60 characters or less.")
        elif len(username) < 3:
            error_list.append(
                "Username must be at least 3 characters or more."
            )
        if not re.match("^[a-zA-Z0-9_]*$", username):
            error_list.append(
                "Username can only have ASCII letters, numbers, or _"
            )
        elif User.objects.filter(username__iexact=username).exists():
            error_list.append(f'The username "{username}" is already taken')

        if len(displayname) > 60:
            error_list.append("Display name must be 60 characters or less.")

        if len(email) > 60:
            error_list.append("Email must be 60 characters or less.")
        else:
            try:
                validate_email(email)
                if User.objects.filter(email__iexact=email).exists():
                    error_list.append("This email is already being used.")
            except ValidationError:
                error_list.append("Email address is invalid.")

        password_lower = password1.lower()
        if len(password1) > 128:
            error_list.append("Password must be 128 characters or less.")
        elif password1 != password2:
            error_list.append("The confirmation password doesn't match.")
        else:
            try:
                validate_password(password1)
                if (
                    password_lower == username.lower()
                    or password_lower == displayname.lower()
                    or password_lower == email.split("@")[0].lower()
                ):
                    error_list.append(
                        "Password is to similar to your name or email"
                    )

            except ValidationError as e:
                error_list += [str(msg) for msg in e.messages]

        if not error_list:
            try:
                User.objects.create_user(
                    username,
                    email=email,
                    password=password1,
                    virtual=False,
                    first_name=displayname,
                )
                user = authenticate(
                    request, username=username, password=password1
                )
                if not user:
                    error_list += (
                        "There was a problem logging you "
                        + "in. Try logging in from the main page."
                    )
                else:
                    login(request, user)
            except:
                error_list.append(
                    "Sorry, there was an unexpected error while "
                    + "creating your account. Please try again later"
                )

        if error_list:
            return render(
                request,
                "registration/signup.html",
                {
                    "error_list": error_list,
                    "username": username,
                    "displayname": displayname,
                    "email": email,
                },
            )

        return redirect("/firstratings")


class DisplayNameChangeView(LoginRequiredMixin, AbstractAccount):
    template_name = "registration/displayname_change.html"

    def post(self, request):
        old_displayname = request.user.first_name
        new_displayname = str(self.request.POST.get("new_displayname")).strip()

        error_text = ""
        if not new_displayname:
            error_text = "You must provide a new display name."
        elif new_displayname == old_displayname:
            error_text = (
                f'Your display name already is "{new_displayname}".'
                "Choose a different name."
            )
        elif len(new_displayname) > 60:
            error_text = "Display name must be 60 characters or less."

        if not error_text:
            try:
                user = User.objects.get(username=request.user.username)
                user.first_name = new_displayname
                user.save()
            except:
                error_text = (
                    "Sorry, there was an unexpected error while changing your "
                    "display name. Please try again later."
                )

        if error_text:
            return render(
                request,
                "registration/displayname_change.html",
                {"error_text": error_text},
            )
        return render(
            request,
            "registration/displayname_change_done.html",
            {"new_displayname": new_displayname},
        )


class EmailChangeView(LoginRequiredMixin, AbstractAccount):
    template_name = "registration/email_change.html"

    def post(self, request):
        old_email = request.user.email
        new_email = str(self.request.POST.get("new_email")).strip()

        error_text = ""
        if not new_email:
            error_text = "You must provide a new email address."
        elif new_email == old_email:
            error_text = f'Your email already is "{new_email}"'
        elif len(new_email) > 60:
            error_text = "The email address must be 60 characters or less."
        elif User.objects.filter(email__iexact=new_email).exists():
            error_text = "Someone is already using this email address."
        else:
            try:
                validate_email(new_email)
            except ValidationError:
                error_text = "Email address is invalid."

        if not error_text:
            try:
                user = User.objects.get(username=request.user.username)
                user.email = new_email
                user.save()
            except:
                error_text = (
                    "Sorry, there was an unexpected error while changing your "
                    "email address. Please try again later."
                )

        if error_text:
            return render(
                request,
                "registration/email_change.html",
                {"error_text": error_text},
            )

        return render(
            request,
            "registration/email_change_done.html",
            {"new_email": new_email},
        )


class UserNameChangeView(LoginRequiredMixin, AbstractAccount):
    template_name = "registration/username_change.html"

    def post(self, request):
        old_username = request.user.username
        new_username = str(self.request.POST.get("new_username")).strip()

        error_text = ""

        if not new_username:
            error_text = "You must provide a new username."
        elif len(new_username) > 60:
            error_text = "Username must be 60 characters or less."
        elif len(new_username) < 3:
            error_text = "Username must be at least 3 characters or more."
        elif not re.match("^[a-zA-Z0-9_]*$", new_username):
            error_text = "Username can only have ASCII letters, numbers, or _"
        elif new_username == old_username:
            error_text = (
                f'Your user name already is "{new_username}". '
                "Choose a different name."
            )
        elif User.objects.filter(username__iexact=new_username).exists():
            error_text = f'The username "{new_username}" is already taken'

        if not error_text:
            try:
                user = User.objects.get(username=request.user.username)
                user.username = new_username
                user.save()
            except:
                error_text = (
                    "Sorry, there was an unexpected error "
                    + "while changing your username. Please try again later."
                )

        if error_text:
            return render(
                request,
                "registration/username_change.html",
                {"error_text": error_text},
            )

        return render(
            request,
            "registration/username_change_done.html",
            {"new_username": new_username},
        )


class AccountDeleteView(LoginRequiredMixin, AbstractAccount):
    template_name = "registration/account_delete.html"

    def post(self, request):
        username = request.user.username
        typed_username = self.request.POST.get("username")
        if typed_username != username:
            error_text = (
                'Your user name isn\'t "<b>{}</b>". You must type your '
                + "user name exactly in order to delete your account."
            )
            error_text = error_text.format(typed_username)
            return render(
                request,
                "registration/account_delete.html",
                {"error_text": error_text},
            )

        user = User.objects.get(username=username)
        user.delete()
        return render(
            request,
            "registration/account_delete_done.html",
            {"deleted_user": username},
        )
