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


class EducationProgram(models.Model):
    class StudyForm(models.TextChoices):
        FULL_TIME = 'FULL_TIME', 'Очная'
        PART_TIME = 'PART_TIME', 'Заочная'
        MIXED = 'MIXED', 'Очно-заочная (вечерняя)'

    specialty = models.ForeignKey(
        Specialty,
        on_delete=models.CASCADE,
        related_name='programs',
        verbose_name='Направление подготовки'
    )
    study_form = models.CharField(
        max_length=20,
        choices=StudyForm.choices,
        default=StudyForm.FULL_TIME,
        verbose_name='Форма обучения'
    )
    tuition_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        verbose_name='Стоимость обучения в год (руб.)'
    )
    duration = models.CharField(
        max_length=50,
        verbose_name='Срок обучения',
        help_text='Например: 4 года, 4 года 6 месяцев, 2 года'
    )
    is_active = models.BooleanField(
        default=True,
        verbose_name='Ведется набор'
    )

    class Meta:
        verbose_name = 'Образовательная программа'
        verbose_name_plural = 'Образовательные программы'
        ordering = ['specialty', 'study_form']
        unique_together = ('specialty', 'study_form')

    def __str__(self):
        return f"{self.specialty.name} ({self.get_study_form_display()}) — {self.duration}"


class ExamSubject(models.Model):
    name = models.CharField(
        max_length=150,
        unique=True,
        verbose_name='Наименование предмета'
    )
    min_score = models.PositiveIntegerField(
        default=39,
        verbose_name='Минимальный балл'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Описание / Примечания'
    )

    class Meta:
        verbose_name = 'Предмет ЕГЭ / вступительных'
        verbose_name_plural = 'Предметы ЕГЭ / вступительных'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} (мин. балл: {self.min_score})"


