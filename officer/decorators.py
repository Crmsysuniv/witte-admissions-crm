from functools import wraps
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied
from accounts.models import User


def is_officer_or_admin(user):
    """
    Проверяет, обладает ли пользователь полномочиями сотрудника приемной комиссии или администратора.
    Возвращает True, если:
    - роль пользователя равна OFFICER или ADMIN;
    - установлены флаги is_officer, is_admin_role, is_staff или is_superuser.
    """
    if not user or not user.is_authenticated:
        return False

    return bool(
        getattr(user, 'role', None) in [User.Role.OFFICER, User.Role.ADMIN]
        or getattr(user, 'is_officer', False)
        or getattr(user, 'is_admin_role', False)
        or getattr(user, 'is_staff', False)
        or getattr(user, 'is_superuser', False)
    )


def officer_required(view_func):
    """
    Декоратор для ограничения доступа только авторизованным сотрудникам приемной комиссии и администраторам.
    - Если пользователь не авторизован -> перенаправляет на страницу входа (/login/?next=...).
    - Если пользователь авторизован, но не имеет роли OFFICER или ADMIN -> возбуждает PermissionDenied (HTTP 403).
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return login_required(view_func)(request, *args, **kwargs)

        if not is_officer_or_admin(request.user):
            raise PermissionDenied(
                "Доступ к рабочему месту сотрудника приемной комиссии разрешен только сотрудникам приемной комиссии (OFFICER) и администраторам (ADMIN)."
            )
        return view_func(request, *args, **kwargs)

    return _wrapped_view


class OfficerRequiredMixin(AccessMixin):
    """
    Миксин для Class-Based Views, ограничивающий доступ только для сотрудников приемной комиссии и администраторов.
    Если пользователь не авторизован — перенаправляет на страницу логина.
    Если роль не соответствует — вызывает ошибку 403 (PermissionDenied).
    """
    permission_denied_message = (
        "Доступ к разделу сотрудника приемной комиссии разрешен только пользователям с ролью OFFICER или ADMIN."
    )

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if not is_officer_or_admin(request.user):
            raise PermissionDenied(self.permission_denied_message)

        return super().dispatch(request, *args, **kwargs)

