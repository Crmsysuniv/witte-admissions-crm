from django.conf import settings
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


class ApplicantProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='applicant_profile',
        verbose_name='Пользователь'
    )
    birth_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Дата рождения'
    )
    snils = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='СНИЛС'
    )
    passport_series = models.CharField(
        max_length=10,
        blank=True,
        verbose_name='Серия паспорта'
    )
    passport_number = models.CharField(
        max_length=10,
        blank=True,
        verbose_name='Номер паспорта'
    )
    passport_issued_by = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Кем выдан паспорт'
    )
    passport_issue_date = models.DateField(
        null=True,
        blank=True,
        verbose_name='Дата выдачи паспорта'
    )
    passport_department_code = models.CharField(
        max_length=10,
        blank=True,
        verbose_name='Код подразделения'
    )
    address = models.TextField(
        blank=True,
        verbose_name='Адрес проживания/регистрации'
    )

    class Meta:
        verbose_name = 'Профиль абитуриента'
        verbose_name_plural = 'Профили абитуриентов'

    def __str__(self):
        return f"Профиль абитуриента: {self.user.get_full_name() or self.user.username}"


class OfficerProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='officer_profile',
        verbose_name='Пользователь'
    )
    position = models.CharField(
        max_length=150,
        blank=True,
        verbose_name='Должность'
    )
    cabinet = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Рабочий кабинет'
    )

    class Meta:
        verbose_name = 'Профиль сотрудника комиссии'
        verbose_name_plural = 'Профили сотрудников комиссии'

    def __str__(self):
        return f"Профиль сотрудника: {self.user.get_full_name() or self.user.username} ({self.position or 'Должность не указана'})"


