from django.conf import settings
from django.db import models
from django.utils import timezone


class FeedbackMessage(models.Model):
    class Status(models.TextChoices):
        NEW = 'NEW', 'Новое'
        IN_PROGRESS = 'IN_PROGRESS', 'В обработке'
        RESOLVED = 'RESOLVED', 'Обработано / Ответ дан'
        REJECTED = 'REJECTED', 'Отклонено / Спам'

    full_name = models.CharField(
        max_length=200,
        verbose_name='ФИО'
    )
    phone = models.CharField(
        max_length=20,
        verbose_name='Номер телефона'
    )
    email = models.EmailField(
        verbose_name='Электронная почта'
    )
    subject = models.CharField(
        max_length=255,
        verbose_name='Тема обращения'
    )
    message = models.TextField(
        verbose_name='Текст сообщения'
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
        verbose_name='Статус обработки'
    )
    officer_response = models.TextField(
        blank=True,
        verbose_name='Ответ сотрудника'
    )
    responded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='responded_feedbacks',
        verbose_name='Ответивший сотрудник'
    )
    responded_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Дата ответа'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата отправки'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )

    class Meta:
        verbose_name = 'Сообщение обратной связи'
        verbose_name_plural = 'Сообщения обратной связи'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.subject} — {self.full_name} ({self.get_status_display()})"

    def mark_resolved(self, response_text, officer=None):
        self.officer_response = response_text
        self.status = self.Status.RESOLVED
        self.responded_at = timezone.now()
        if officer:
            self.responded_by = officer
        self.save()

