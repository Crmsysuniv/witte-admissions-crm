from django.db import models


class Faculty(models.Model):
    name = models.CharField(
        max_length=255,
        unique=True,
        verbose_name='Название факультета'
    )
    code = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Код / Аббревиатура'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Описание факультета'
    )

    class Meta:
        verbose_name = 'Факультет'
        verbose_name_plural = 'Факультеты'
        ordering = ['name']

    def __str__(self):
        if self.code:
            return f"{self.name} ({self.code})"
        return self.name


class Specialty(models.Model):
    class EducationLevel(models.TextChoices):
        BACHELOR = 'BACHELOR', 'Бакалавриат'
        SPECIALIST = 'SPECIALIST', 'Специалитет'
        MASTER = 'MASTER', 'Магистратура'
        POSTGRADUATE = 'POSTGRADUATE', 'Аспирантура'
        COLLEGE = 'COLLEGE', 'Колледж (СПОР)'

    faculty = models.ForeignKey(
        Faculty,
        on_delete=models.CASCADE,
        related_name='specialties',
        verbose_name='Факультет'
    )
    code = models.CharField(
        max_length=20,
        verbose_name='Код направления подготовки'
    )
    name = models.CharField(
        max_length=255,
        verbose_name='Название направления подготовки'
    )
    education_level = models.CharField(
        max_length=20,
        choices=EducationLevel.choices,
        default=EducationLevel.BACHELOR,
        verbose_name='Уровень образования'
    )
    budget_places = models.PositiveIntegerField(
        default=0,
        verbose_name='Бюджетные места'
    )
    paid_places = models.PositiveIntegerField(
        default=0,
        verbose_name='Платные места'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активно для приема'
    )

    class Meta:
        verbose_name = 'Направление подготовки'
        verbose_name_plural = 'Направления подготовки'
        ordering = ['code', 'name']
        unique_together = ('code', 'name', 'education_level')

    def __str__(self):
        return f"{self.code} {self.name} ({self.get_education_level_display()})"

    @property
    def total_places(self):
        return self.budget_places + self.paid_places

