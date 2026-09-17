from django.contrib import admin

from .models import UserProfile, Role


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "phone_number",
        "gender",
    )

    search_fields = (
        "user__username",
        "user__email",
        "phone_number",
    )

    list_filter = (
        "gender",
    )


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):

    list_display = (
        "name",
    )

    search_fields = (
        "name",
    )