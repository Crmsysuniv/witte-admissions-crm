from functools import wraps
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from accounts.models import User


def officer_required(view_func):
    """
    Декоратор для ограничения доступа только авторизованным сотрудникам приемной комиссии и администраторам.
    - Если пользователь не авторизован -> перенаправляет на страницу входа (/login/?next=...).
    - Если пользователь авторизован, но не является сотрудником/администратором -> возбуждает PermissionDenied (HTTP 403).
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return login_required(view_func)(request, *args, **kwargs)

        is_authorized = (
            getattr(request.user, 'role', None) in [User.Role.OFFICER, User.Role.ADMIN]
            or getattr(request.user, 'is_officer', False)
            or getattr(request.user, 'is_staff', False)
            or getattr(request.user, 'is_superuser', False)
        )
        if not is_authorized:
            raise PermissionDenied(
                "Доступ к рабочему месту сотрудника приемной комиссии разрешен только уполномоченным сотрудникам и администраторам."
            )
        return view_func(request, *args, **kwargs)

    return _wrapped_view
