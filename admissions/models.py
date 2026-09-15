from django.conf import settings
from django.core.validators import FileExtensionValidator, MinValueValidator, MaxValueValidator
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


class Application(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Черновик'
        SUBMITTED = 'SUBMITTED', 'Подано'
        UNDER_REVIEW = 'UNDER_REVIEW', 'На рассмотрении'
        DOCUMENTS_REQUIRED = 'DOCUMENTS_REQUIRED', 'Требуются документы'
        APPROVED = 'APPROVED', 'Одобрено (допущен к конкурсу)'
        ENROLLED = 'ENROLLED', 'Зачислен'
        REJECTED = 'REJECTED', 'Отклонено'
        WITHDRAWN = 'WITHDRAWN', 'Отозвано'

    class FinancingType(models.TextChoices):
        BUDGET = 'BUDGET', 'Бюджетная основа'
        PAID = 'PAID', 'Платная основа (договор)'

    applicant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='applications',
        verbose_name='Абитуриент'
    )
    program = models.ForeignKey(
        EducationProgram,
        on_delete=models.PROTECT,
        related_name='applications',
        verbose_name='Выбранная программа'
    )
    status = models.CharField(
        max_length=30,
        choices=Status.choices,
        default=Status.SUBMITTED,
        verbose_name='Статус заявки'
    )
    financing_type = models.CharField(
        max_length=20,
        choices=FinancingType.choices,
        default=FinancingType.BUDGET,
        verbose_name='Основа обучения'
    )
    submission_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата подачи'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Дата обновления'
    )
    officer_comment = models.TextField(
        blank=True,
        verbose_name='Комментарий приемной комиссии'
    )

    class Meta:
        verbose_name = 'Заявление на поступление'
        verbose_name_plural = 'Заявления на поступление'
        ordering = ['-submission_date']

    def __str__(self):
        full_name = self.applicant.get_full_name() or self.applicant.username
        return f"Заявление №{self.id} — {full_name} — {self.program.specialty.name} ({self.get_status_display()})"

    @property
    def total_score(self):
        return sum(s.score for s in self.exam_scores.all())



def application_document_upload_to(instance, filename):
    return f"applications/{instance.application_id}/documents/{instance.document_type}_{filename}"


class ApplicationDocument(models.Model):
    class DocumentType(models.TextChoices):
        PASSPORT = 'PASSPORT', 'Скан паспорта'
        CERTIFICATE = 'CERTIFICATE', 'Аттестат'
        DIPLOMA = 'DIPLOMA', 'Диплом'
        PRIVILEGE = 'PRIVILEGE', 'Документ о льготах'
        OTHER = 'OTHER', 'Иной документ'

    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='documents',
        verbose_name='Заявление'
    )
    document_type = models.CharField(
        max_length=30,
        choices=DocumentType.choices,
        verbose_name='Тип документа'
    )
    file = models.FileField(
        upload_to=application_document_upload_to,
        validators=[
            FileExtensionValidator(
                allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'],
                message='Разрешены только файлы форматов PDF, JPG, JPEG, PNG.'
            )
        ],
        verbose_name='Файл документа'
    )
    comment = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='Комментарий'
    )
    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата загрузки'
    )
    is_verified = models.BooleanField(
        default=False,
        verbose_name='Проверен'
    )

    class Meta:
        verbose_name = 'Документ заявления'
        verbose_name_plural = 'Документы заявлений'
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.get_document_type_display()} — {self.application}"


class ExamScore(models.Model):
    class ExamType(models.TextChoices):
        EGE = 'EGE', 'Единый государственный экзамен (ЕГЭ)'
        INTERNAL = 'INTERNAL', 'Вступительное испытание вуза'
        OLYMPIAD = 'OLYMPIAD', 'Олимпиада / Особое право'

    application = models.ForeignKey(
        Application,
        on_delete=models.CASCADE,
        related_name='exam_scores',
        verbose_name='Заявление'
    )
    subject = models.ForeignKey(
        ExamSubject,
        on_delete=models.PROTECT,
        related_name='scores',
        verbose_name='Предмет'
    )
    score = models.PositiveIntegerField(
        validators=[
            MinValueValidator(0, message='Балл не может быть меньше 0.'),
            MaxValueValidator(100, message='Балл не может превышать 100.')
        ],
        verbose_name='Балл'
    )
    exam_type = models.CharField(
        max_length=20,
        choices=ExamType.choices,
        default=ExamType.EGE,
        verbose_name='Тип испытания'
    )
    year = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='Год сдачи'
    )
    document_number = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Номер свидетельства / документа'
    )
    is_verified = models.BooleanField(
        default=False,
        verbose_name='Балл подтвержден'
    )

    class Meta:
        verbose_name = 'Балл вступительного испытания'
        verbose_name_plural = 'Баллы вступительных испытаний'
        unique_together = ('application', 'subject')
        ordering = ['subject__name']

    def __str__(self):
        return f"{self.subject.name}: {self.score} б. ({self.get_exam_type_display()}) — {self.application}"

    @property
    def is_passing(self):
        return self.score >= self.subject.min_score





