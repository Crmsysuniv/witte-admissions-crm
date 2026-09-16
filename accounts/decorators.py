from functools import wraps
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied
from accounts.models import User


def is_admin_user(user):
    """
    Проверяет, обладает ли пользователь правами администратора CRM.
    Возвращает True, если:
    - роль пользователя равна ADMIN;
    - установлены флаги is_admin_role, is_staff или is_superuser.
    """
    if not user or not user.is_authenticated:
        return False

    return bool(
        getattr(user, 'role', None) == User.Role.ADMIN
        or getattr(user, 'is_admin_role', False)
        or getattr(user, 'is_staff', False)
        or getattr(user, 'is_superuser', False)
    )


def admin_required(view_func):
    """
    Декоратор для ограничения доступа только авторизованным администраторам системы.
    - Неавторизованный пользователь перенаправляется на /login/?next=...
    - Авторизованный пользователь без прав администратора получает HTTP 403 (PermissionDenied).
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return login_required(view_func)(request, *args, **kwargs)

        if not is_admin_user(request.user):
            raise PermissionDenied(
                "Доступ к главному аналитическому дашборду руководителя разрешен только администраторам системы (ADMIN)."
            )
        return view_func(request, *args, **kwargs)

    return _wrapped_view


class AdminRequiredMixin(AccessMixin):
    """
    Миксин для Class-Based Views, требующий прав администратора.
    """
    permission_denied_message = (
        "Доступ к разделу аналитики разрешен только пользователям с ролью ADMIN."
    )

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if not is_admin_user(request.user):
            raise PermissionDenied(self.permission_denied_message)

        return super().dispatch(request, *args, **kwargs)
