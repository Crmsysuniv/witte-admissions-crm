from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from accounts.models import User


def applicant_required(view_func):
    """
    Декоратор для ограничения доступа только авторизованным пользователям с ролью APPLICANT.
    - Если пользователь не авторизован -> перенаправляет на страницу входа (/login/?next=...).
    - Если пользователь авторизован, но его роль НЕ APPLICANT -> возбуждает PermissionDenied (HTTP 403).
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return login_required(view_func)(request, *args, **kwargs)

        is_applicant = (
            getattr(request.user, 'role', None) == User.Role.APPLICANT
            or getattr(request.user, 'is_applicant', False)
        )
        if not is_applicant:
            raise PermissionDenied(
                "Доступ к личному кабинету абитуриента разрешен только пользователям с ролью «Абитуриент»."
            )
        return view_func(request, *args, **kwargs)

    return _wrapped_view
