import re
from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from .models import User, ApplicantProfile


def validate_password_strength(password):
    """
    Комплексная валидация надежности пароля:
    - Длина не менее 8 символов
    - Наличие заглавных букв
    - Наличие строчных букв
    - Наличие цифр
    - Наличие специальных символов
    """
    errors = []
    if len(password) < 8:
        errors.append('Пароль должен содержать не менее 8 символов.')
    if not re.search(r'[A-ZА-Я]', password):
        errors.append('Пароль должен содержать как минимум одну заглавную букву (A-Z или А-Я).')
    if not re.search(r'[a-zа-я]', password):
        errors.append('Пароль должен содержать как минимум одну строчную букву (a-z или а-я).')
    if not re.search(r'\d', password):
        errors.append('Пароль должен содержать хотя бы одну цифру (0-9).')
    if not re.search(r'[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?~`]', password):
        errors.append('Пароль должен содержать хотя бы один специальный символ (!@#$%^&* и т.д.).')

    if errors:
        raise ValidationError(errors)


class ApplicantRegistrationForm(forms.ModelForm):
    """
    Форма самостоятельной регистрации абитуриента в CRM МУ им. С.Ю. Витте.
    Автоматически присваивает пользователю роль APPLICANT и создает профиль абитуриента.
    """
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

    username = forms.CharField(
        label='Логин для входа',
        max_length=150,
        required=True,
        help_text='Латинские буквы, цифры, дефис и подчеркивание (от 3 до 30 символов)',
        widget=forms.TextInput(attrs={
            'placeholder': 'ivanov_2026',
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 text-sm bg-slate-50 focus:bg-white focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all',
            'autocomplete': 'username',
        })
    )

    email = forms.EmailField(
        label='Электронная почта (Email)',
        required=True,
        help_text='На этот адрес будут направляться уведомления о ходе приема',
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
        })
    )

    password1 = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Придумайте надежный пароль',
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 text-sm bg-slate-50 focus:bg-white focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all pr-10',
            'autocomplete': 'new-password',
            '@input': 'calculateStrength($event.target.value)',
        })
    )

    password2 = forms.CharField(
        label='Повторите пароль',
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Повторите пароль для проверки',
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 text-sm bg-slate-50 focus:bg-white focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all',
            'autocomplete': 'new-password',
            '@input': 'checkMatch($event.target.value)',
        })
    )

    consent = forms.BooleanField(
        label='Я даю согласие на обработку персональных данных в соответствии с 152-ФЗ РФ',
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 rounded text-blue-600 focus:ring-blue-500 border-slate-300 mt-0.5',
        })
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'phone')

    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if len(username) < 3:
            raise ValidationError('Логин должен содержать не менее 3 символов.')
        if not re.match(r'^[a-zA-Z0-9_.-]+$', username):
            raise ValidationError('Логин может содержать только латинские буквы, цифры, дефис, точку и подчеркивание.')
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError('Пользователь с таким логином уже зарегистрирован.')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError('Пользователь с таким email уже зарегистрирован. Воспользуйтесь формой входа.')
        return email

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        digits = re.sub(r'\D', '', phone)
        if len(digits) < 10 or len(digits) > 12:
            raise ValidationError('Укажите корректный номер телефона (от 10 до 11 цифр).')
        return phone

    def clean_password1(self):
        password1 = self.cleaned_data.get('password1')
        if password1:
            # 1. Комплексная проверка надежности (длина, регистр, цифры, спецсимволы)
            validate_password_strength(password1)
            # 2. Стандартные валидаторы Django (CommonPasswordValidator, UserAttributeSimilarityValidator и др.)
            temp_user = User(
                username=self.cleaned_data.get('username', ''),
                email=self.cleaned_data.get('email', ''),
                first_name=self.cleaned_data.get('first_name', ''),
                last_name=self.cleaned_data.get('last_name', ''),
            )
            validate_password(password1, user=temp_user)
        return password1

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get('password1')
        p2 = cleaned_data.get('password2')

        if p1 and p2 and p1 != p2:
            self.add_error('password2', 'Введенные пароли не совпадают.')

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        # АВТОМАТИЧЕСКОЕ И СТРОГОЕ НАЗНАЧЕНИЕ РОЛИ АБИТУРИЕНТА
        user.role = User.Role.APPLICANT
        user.is_staff = False
        user.is_superuser = False
        user.set_password(self.cleaned_data['password1'])

        # Если указано отчество, сохраняем его в first_name или профиле
        patronymic = self.cleaned_data.get('patronymic', '').strip()
        if patronymic:
            # В стандартном поле first_name можно сохранить "Имя Отчество"
            user.first_name = f"{user.first_name} {patronymic}".strip()

        if commit:
            user.save()
            # Автоматическое создание профиля абитуриента
            ApplicantProfile.objects.get_or_create(user=user)

        return user
