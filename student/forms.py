import re
from datetime import date
from django import forms
from django.core.exceptions import ValidationError
from accounts.models import User, ApplicantProfile
from admissions.models import Faculty, Specialty, EducationProgram, Application


class StudentProfileForm(forms.Form):
    """
    Форма редактирования и заполнения персональных данных абитуриента (student/profile.html).
    Включает:
    - Базовые учетные и контактные данные (ФИО, Email, Телефон);
    - Демографические данные (Дата рождения);
    - Идентификационные номера (СНИЛС);
    - Паспортные данные гражданина РФ (Серия, Номер, Кем выдан, Дата выдачи, Код подразделения);
    - Адресную информацию (Адрес постоянной регистрации и фактического проживания).
    """

    # 1. Основные учетные и контактные данные
    last_name = forms.CharField(
        label='Фамилия',
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'Иванов',
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 text-sm bg-slate-50 focus:bg-white focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all',
            'autocomplete': 'family-name',
        })
    )

    first_name = forms.CharField(
        label='Имя',
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': 'Иван',
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 text-sm bg-slate-50 focus:bg-white focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all',
            'autocomplete': 'given-name',
        })
    )

    patronymic = forms.CharField(
        label='Отчество',
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'Иванович (при наличии)',
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 text-sm bg-slate-50 focus:bg-white focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all',
            'autocomplete': 'additional-name',
        })
    )

    email = forms.EmailField(
        label='Электронная почта (Email)',
        required=True,
        widget=forms.EmailInput(attrs={
            'placeholder': 'applicant@example.ru',
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 text-sm bg-slate-50 focus:bg-white focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all',
            'autocomplete': 'email',
        })
    )

    phone = forms.CharField(
        label='Контактный телефон',
        max_length=25,
        required=True,
        widget=forms.TextInput(attrs={
            'placeholder': '+7 (999) 000-00-00',
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 text-sm bg-slate-50 focus:bg-white focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all',
            'autocomplete': 'tel',
            '@input': 'formatPhone($event)',
        })
    )

    birth_date = forms.DateField(
        label='Дата рождения',
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 text-sm bg-slate-50 focus:bg-white focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all',
        })
    )

    # 2. Идентификатор СНИЛС
    snils = forms.CharField(
        label='Страховой номер СНИЛС',
        max_length=20,
        required=False,
        help_text='11 цифр страхового свидетельства (формат: 000-000-000 00)',
        widget=forms.TextInput(attrs={
            'placeholder': '000-000-000 00',
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 text-sm bg-slate-50 focus:bg-white focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all font-mono',
            '@input': 'formatSnils($event)',
        })
    )

    # 3. Паспортные данные гражданина РФ
    passport_series = forms.CharField(
        label='Серия паспорта',
        max_length=10,
        required=False,
        help_text='4 цифры серии (например, 45 15)',
        widget=forms.TextInput(attrs={
            'placeholder': '45 15',
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 text-sm bg-slate-50 focus:bg-white focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all font-mono',
            'maxlength': '5',
            '@input': 'formatPassportSeries($event)',
        })
    )

    passport_number = forms.CharField(
        label='Номер паспорта',
        max_length=10,
        required=False,
        help_text='6 цифр номера',
        widget=forms.TextInput(attrs={
            'placeholder': '123456',
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 text-sm bg-slate-50 focus:bg-white focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all font-mono',
            'maxlength': '6',
            '@input': 'formatDigitsOnly($event, 6)',
        })
    )

    passport_issued_by = forms.CharField(
        label='Кем выдан паспорт',
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={
            'placeholder': 'ГУ МВД России по г. Москве',
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 text-sm bg-slate-50 focus:bg-white focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all',
        })
    )

    passport_issue_date = forms.DateField(
        label='Дата выдачи паспорта',
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 text-sm bg-slate-50 focus:bg-white focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all',
        })
    )

    passport_department_code = forms.CharField(
        label='Код подразделения',
        max_length=10,
        required=False,
        help_text='6 цифр (формат: 770-001)',
        widget=forms.TextInput(attrs={
            'placeholder': '770-001',
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 text-sm bg-slate-50 focus:bg-white focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all font-mono',
            'maxlength': '7',
            '@input': 'formatDepartmentCode($event)',
        })
    )

    # 4. Адресная информация
    address = forms.CharField(
        label='Адрес постоянной регистрации и фактического проживания',
        required=False,
        widget=forms.Textarea(attrs={
            'placeholder': 'Индекс, регион, город, улица, дом, корпус, квартира',
            'rows': 3,
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 text-sm bg-slate-50 focus:bg-white focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all',
        })
    )

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        self.profile = getattr(user, 'applicant_profile', None) if user else None

        if user and 'initial' not in kwargs:
            first_name = user.first_name or ''
            parts = first_name.split(' ', 1) if first_name else ['', '']
            actual_first_name = parts[0]
            patronymic = parts[1] if len(parts) > 1 else ''

            initial_data = {
                'last_name': user.last_name,
                'first_name': actual_first_name,
                'patronymic': patronymic,
                'email': user.email,
                'phone': user.phone,
            }

            if self.profile:
                initial_data.update({
                    'birth_date': self.profile.birth_date,
                    'snils': self.profile.snils,
                    'passport_series': self.profile.passport_series,
                    'passport_number': self.profile.passport_number,
                    'passport_issued_by': self.profile.passport_issued_by,
                    'passport_issue_date': self.profile.passport_issue_date,
                    'passport_department_code': self.profile.passport_department_code,
                    'address': self.profile.address,
                })
            kwargs['initial'] = initial_data

        super().__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        query = User.objects.filter(email__iexact=email)
        if self.user and self.user.pk:
            query = query.exclude(pk=self.user.pk)
        if query.exists():
            raise ValidationError('Пользователь с таким адресом электронной почты уже зарегистрирован в системе.')
        return email

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        digits = re.sub(r'\D', '', phone)
        if len(digits) < 10 or len(digits) > 12:
            raise ValidationError('Укажите корректный номер телефона (от 10 до 11 цифр).')
        return phone

    def clean_birth_date(self):
        birth_date = self.cleaned_data.get('birth_date')
        if birth_date:
            today = date.today()
            if birth_date > today:
                raise ValidationError('Дата рождения не может быть в будущем.')
            if birth_date.year < 1930:
                raise ValidationError('Пожалуйста, укажите корректную дату рождения.')
            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
            if age < 13:
                raise ValidationError('Возраст абитуриента для поступления должен составлять не менее 14 лет.')
        return birth_date

    def clean_snils(self):
        snils = self.cleaned_data.get('snils', '').strip()
        if snils:
            digits = re.sub(r'\D', '', snils)
            if len(digits) != 11:
                raise ValidationError('СНИЛС должен содержать ровно 11 цифр (формат: 000-000-000 00).')
            snils = f"{digits[0:3]}-{digits[3:6]}-{digits[6:9]} {digits[9:11]}"
        return snils

    def clean_passport_series(self):
        series = self.cleaned_data.get('passport_series', '').strip()
        if series:
            digits = re.sub(r'\D', '', series)
            if len(digits) != 4:
                raise ValidationError('Серия паспорта РФ должна содержать ровно 4 цифры (например, 45 15).')
            series = f"{digits[:2]} {digits[2:]}"
        return series

    def clean_passport_number(self):
        number = self.cleaned_data.get('passport_number', '').strip()
        if number:
            digits = re.sub(r'\D', '', number)
            if len(digits) != 6:
                raise ValidationError('Номер паспорта РФ должен содержать ровно 6 цифр.')
            number = digits
        return number

    def clean_passport_department_code(self):
        code = self.cleaned_data.get('passport_department_code', '').strip()
        if code:
            digits = re.sub(r'\D', '', code)
            if len(digits) != 6:
                raise ValidationError('Код подразделения должен содержать ровно 6 цифр (формат: 770-001).')
            code = f"{digits[:3]}-{digits[3:]}"
        return code

    def clean_passport_issue_date(self):
        issue_date = self.cleaned_data.get('passport_issue_date')
        birth_date = self.cleaned_data.get('birth_date')
        if issue_date:
            today = date.today()
            if issue_date > today:
                raise ValidationError('Дата выдачи паспорта не может быть в будущем.')
            if birth_date and issue_date < birth_date:
                raise ValidationError('Дата выдачи паспорта не может быть раньше даты рождения.')
        return issue_date

    def save(self):
        user = self.user
        if not user:
            raise ValueError('Не указан пользователь для сохранения профиля.')

        profile = getattr(user, 'applicant_profile', None)
        if not profile:
            profile, _ = ApplicantProfile.objects.get_or_create(user=user)
            self.profile = profile

        data = self.cleaned_data

        # 1. Сохранение данных пользователя
        user.last_name = data['last_name'].strip()
        first_name = data['first_name'].strip()
        patronymic = data.get('patronymic', '').strip()
        if patronymic:
            user.first_name = f"{first_name} {patronymic}".strip()
        else:
            user.first_name = first_name

        user.email = data['email'].strip().lower()
        user.phone = data['phone'].strip()
        user.save()

        # 2. Сохранение данных профиля абитуриента
        profile.birth_date = data.get('birth_date')
        profile.snils = data.get('snils', '').strip()
        profile.passport_series = data.get('passport_series', '').strip()
        profile.passport_number = data.get('passport_number', '').strip()
        profile.passport_issued_by = data.get('passport_issued_by', '').strip()
        profile.passport_issue_date = data.get('passport_issue_date')
        profile.passport_department_code = data.get('passport_department_code', '').strip()
        profile.address = data.get('address', '').strip()
        return user, profile


class ApplicationSubmissionForm(forms.Form):
    """
    Пошаговая форма подачи заявления на обучение (student/apply.html):
    - Выбор факультета / института;
    - Выбор направления подготовки (специальности);
    - Выбор образовательной программы и формы обучения;
    - Выбор основы обучения (бюджет / договор);
    - Согласие с правилами приема и 152-ФЗ.
    """
    faculty = forms.ModelChoiceField(
        queryset=Faculty.objects.all(),
        required=True,
        label='Факультет / Институт',
        empty_label='— Выберите факультет —',
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 text-sm bg-slate-50 focus:bg-white focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all',
        })
    )

    specialty = forms.ModelChoiceField(
        queryset=Specialty.objects.filter(is_active=True),
        required=True,
        label='Направление подготовки',
        empty_label='— Выберите направление —',
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 text-sm bg-slate-50 focus:bg-white focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all',
        })
    )

    program = forms.ModelChoiceField(
        queryset=EducationProgram.objects.filter(is_active=True),
        required=True,
        label='Форма обучения и программа',
        empty_label='— Выберите форму обучения —',
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 text-sm bg-slate-50 focus:bg-white focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all',
        })
    )

    financing_type = forms.ChoiceField(
        choices=Application.FinancingType.choices,
        required=True,
        initial=Application.FinancingType.BUDGET,
        label='Основа финансирования',
    )

    consent_rules = forms.BooleanField(
        required=True,
        label='Я ознакомлен(а) с Правилами приема в МУ им. С.Ю. Витте на 2026/2027 учебный год',
    )

    consent_data = forms.BooleanField(
        required=True,
        label='Подтверждаю достоверность предоставленных сведений и даю согласие на обработку персональных данных (152-ФЗ)',
    )

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        faculty = cleaned_data.get('faculty')
        specialty = cleaned_data.get('specialty')
        program = cleaned_data.get('program')
        financing_type = cleaned_data.get('financing_type')

        if specialty and faculty and specialty.faculty_id != faculty.id:
            self.add_error('specialty', 'Выбранное направление подготовки не относится к указанному факультету.')

        if program and specialty and program.specialty_id != specialty.id:
            self.add_error('program', 'Выбранная программа обучения не относится к данному направлению подготовки.')

        if self.user:
            # 1. Лимит заявлений (не более 5)
            existing_count = Application.objects.filter(applicant=self.user).count()
            if existing_count >= 5:
                raise ValidationError('Превышен лимит подачи заявлений. По правилам приема 2026 года абитуриент может участвовать в конкурсе максимум по 5 заявлениям.')

            # 2. Дубликат программы и формы финансирования
            if program and financing_type:
                if Application.objects.filter(applicant=self.user, program=program, financing_type=financing_type).exists():
                    raise ValidationError(f'Вы уже подали заявление на программу «{program.specialty.name}» ({program.get_study_form_display()}) с этой основой обучения.')

        return cleaned_data

