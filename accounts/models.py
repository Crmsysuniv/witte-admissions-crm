from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Администратор'
        OFFICER = 'OFFICER', 'Сотрудник приемной комиссии'
        APPLICANT = 'APPLICANT', 'Абитуриент'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.APPLICANT,
        verbose_name='Роль'
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Номер телефона'
    )

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ['-date_joined']

    def __str__(self):
        full_name = self.get_full_name()
        if full_name:
            return f"{full_name} ({self.username}) - {self.get_role_display()}"
        return f"{self.username} - {self.get_role_display()}"

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN or self.is_superuser

    @property
    def is_officer(self):
        return self.role == self.Role.OFFICER

    @property
    def is_applicant(self):
        return self.role == self.Role.APPLICANT

    def save(self, *args, **kwargs):
        if self.role == self.Role.ADMIN:
            self.is_staff = True
        super().save(*args, **kwargs)

