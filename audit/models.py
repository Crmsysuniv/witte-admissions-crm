from django.conf import settings
from django.db import models
from django.utils import timezone


class StatusLog(models.Model):
    application = models.ForeignKey(
        'admissions.Application',
        on_delete=models.CASCADE,
        related_name='status_logs',
        verbose_name='Заявление'
    )
    old_status = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Предыдущий статус'
    )
    new_status = models.CharField(
        max_length=50,
        verbose_name='Новый статус'
    )
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='status_logs',
        verbose_name='Сотрудник'
    )
    changed_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата и время изменения'
    )
    comment = models.TextField(
        blank=True,
        verbose_name='Комментарий к изменению'
    )

    class Meta:
        verbose_name = 'Запись истории статуса'
        verbose_name_plural = 'История изменений статусов'
        ordering = ['-changed_at']

    def __str__(self):
        return f"Заявление №{self.application_id}: {self.old_status or '—'} -> {self.new_status} ({self.changed_at:%d.%m.%Y %H:%M})"


class Notification(models.Model):
    class NotificationType(models.TextChoices):
        INFO = 'INFO', 'Информация'
        STATUS_CHANGE = 'STATUS_CHANGE', 'Изменение статуса'
        DOCUMENT = 'DOCUMENT', 'Документы'
        WARNING = 'WARNING', 'Внимание'
        SUCCESS = 'SUCCESS', 'Успех'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='Получатель'
    )
    title = models.CharField(
        max_length=255,
        verbose_name='Заголовок'
    )
    message = models.TextField(
        verbose_name='Текст уведомления'
    )
    notification_type = models.CharField(
        max_length=20,
        choices=NotificationType.choices,
        default=NotificationType.INFO,
        verbose_name='Тип уведомления'
    )
    application = models.ForeignKey(
        'admissions.Application',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications',
        verbose_name='Связанное заявление'
    )
    is_read = models.BooleanField(
        default=False,
        verbose_name='Прочитано'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата создания'
    )
    read_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата прочтения'
    )

    class Meta:
        verbose_name = 'Уведомление'
        verbose_name_plural = 'Уведомления'
        ordering = ['-created_at']

    def __str__(self):
        return f"Уведомление для {self.user}: {self.title}"

    def mark_as_read(self):
        self.is_read = True
        self.read_at = timezone.now()
        self.save()


class SecurityLog(models.Model):
    class EventType(models.TextChoices):
        LOGIN = 'LOGIN', 'Вход в систему'
        LOGOUT = 'LOGOUT', 'Выход из системы'
        LOGIN_FAILED = 'LOGIN_FAILED', 'Неудачная попытка входа'
        ROLE_CHANGE = 'ROLE_CHANGE', 'Изменение роли/прав'
        STATUS_CHANGE = 'STATUS_CHANGE', 'Смена статуса заявления'
        DOCUMENT_VERIFY = 'DOCUMENT_VERIFY', 'Верификация документов'
        SETTINGS_CHANGE = 'SETTINGS_CHANGE', 'Изменение параметров кампании'
        EXPORT_DATA = 'EXPORT_DATA', 'Экспорт данных (Excel/Word)'
        PASSWORD_CHANGE = 'PASSWORD_CHANGE', 'Смена пароля'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='security_logs',
        verbose_name='Пользователь'
    )
    event_type = models.CharField(
        max_length=50,
        choices=EventType.choices,
        default=EventType.LOGIN,
        verbose_name='Тип события'
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name='IP-адрес'
    )
    user_agent = models.TextField(
        blank=True,
        verbose_name='User-Agent'
    )
    description = models.TextField(
        verbose_name='Описание события'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата и время'
    )

    class Meta:
        verbose_name = 'Запись журнала безопасности'
        verbose_name_plural = 'Журнал безопасности и аудита'
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_event_type_display()}] {self.user or 'Аноним'} — {self.created_at:%d.%m.%Y %H:%M}"


