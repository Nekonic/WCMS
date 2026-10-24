from django.contrib.auth.decorators import user_passes_test


def is_admin(user) -> bool:
    return bool(user is not None and user.is_authenticated and user.is_active and user.is_staff)


admin_required = user_passes_test(is_admin, login_url="accounts:login")
