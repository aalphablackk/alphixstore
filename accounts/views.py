from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.utils.http import url_has_allowed_host_and_scheme
from django.contrib.auth.decorators import login_required
from .models import UserProfile
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import PasswordChangeView
from django.contrib import messages

from .forms import RegisterForm, LoginForm, ProfileForm, UserForm

# Create your views here.
def register(request):

    if request.method == "POST":

        form = RegisterForm(request.POST)

        if form.is_valid():

            user = form.save()

            messages.success(
                request,
                "Account created successfully."
            )

            login(request, user, backend="accounts.backends.UsernameOrEmailBackend")

            return redirect("home")

    else:

        form = RegisterForm()

    return render(
        request,
        "accounts/register.html",
        {
            "form": form
        }
    )
    


def user_login(request):

    if request.method == "POST":

        form = LoginForm(
            request,
            data=request.POST
        )

        if form.is_valid():

            user = form.get_user()

            login(
                request,
                user
            )

            messages.success(
                request,
                f"Welcome back, {request.user.username}!"
            )
            next_url = request.POST.get("next")

            if (
                next_url
                and url_has_allowed_host_and_scheme(
                    next_url,
                    allowed_hosts={request.get_host()}
                )
            ):

                return redirect(next_url)

            return redirect("home")

    else:

        form = LoginForm()

    return render(
        request,
        "accounts/login.html",
        {
            "form": form
        }
    )



def user_logout(request):

    logout(request)
    messages.success(
    request,
    "You have been logged out successfully."
)

    return redirect("login")


@login_required(login_url="/accounts/login/")
def profile(request):

    profile, created = UserProfile.objects.get_or_create(
        user=request.user
    )

    if request.method == "POST":

        user_form = UserForm(
            request.POST,
            instance=request.user
        )

        profile_form = ProfileForm(
            request.POST,
            request.FILES,
            instance=profile
        )

        if user_form.is_valid() and profile_form.is_valid():

            user_form.save()

            profile_form.save()
            messages.success(
                request,
                "Your profile has been updated successfully."
            )

            return redirect("profile")

    else:

        user_form = UserForm(
            instance=request.user
        )

        profile_form = ProfileForm(
            instance=profile
        )

    return render(
        request,
        "accounts/profile.html",
        {
            "user_form": user_form,
            "profile_form": profile_form,
            "profile": profile,
        }
    )





class CustomPasswordChangeView(
    LoginRequiredMixin,
    PasswordChangeView
):
    template_name = "accounts/password_change.html"
    success_url = "/accounts/password-change/done/"