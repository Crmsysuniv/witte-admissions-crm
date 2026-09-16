from audit.models import SecurityLog


def get_client_ip(request):
    """Получить реальный IP адрес клиента из запроса."""
    if not request:
        return None
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def log_security_event(request=None, event_type=SecurityLog.EventType.LOGIN, description="", user=None):
    """
    Зафиксировать событие безопасности и аудита в SecurityLog.
    """
    if request:
        if not user and hasattr(request, 'user') and request.user.is_authenticated:
            user = request.user
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')[:500] if request.META.get('HTTP_USER_AGENT') else ''
    else:
        ip_address = None
        user_agent = ''

    return SecurityLog.objects.create(
        user=user,
        event_type=event_type,
        ip_address=ip_address,
        user_agent=user_agent,
        description=description
    )
