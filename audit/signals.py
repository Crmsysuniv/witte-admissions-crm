from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver
from audit.models import SecurityLog
from audit.utils import log_security_event


@receiver(user_logged_in)
def log_user_logged_in(sender, request, user, **kwargs):
    log_security_event(
        request=request,
        event_type=SecurityLog.EventType.LOGIN,
        description=f"Успешный вход пользователя {user.email} (Роль: {user.get_role_display()})",
        user=user
    )


@receiver(user_logged_out)
def log_user_logged_out(sender, request, user, **kwargs):
    if user and user.is_authenticated:
        log_security_event(
            request=request,
            event_type=SecurityLog.EventType.LOGOUT,
            description=f"Выход из системы пользователя {user.email}",
            user=user
        )


@receiver(user_login_failed)
def log_user_login_failed(sender, credentials, request, **kwargs):
    username = credentials.get('username') or credentials.get('email') or 'Не указан'
    log_security_event(
        request=request,
        event_type=SecurityLog.EventType.LOGIN_FAILED,
        description=f"Неудачная попытка входа с логином/email: {username}",
        user=None
    )
