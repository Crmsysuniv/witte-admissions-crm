import re
from django import forms
from django.core.exceptions import ValidationError
from .models import FeedbackMessage

SUBJECT_CHOICES = [
    ('', '— Выберите тему обращения —'),
    ('Поступление на бакалавриат / специалитет', 'Поступление на бакалавриат / специалитет'),
    ('Поступление в Колледж МУ им. С.Ю. Витте', 'Поступление в Колледж МУ им. С.Ю. Витте'),
    ('Магистратура и аспирантура', 'Магистратура и аспирантура'),
    ('Вступительные испытания и минимальные баллы', 'Вступительные испытания и минимальные баллы'),
    ('Стоимость обучения, скидки и кредит 3%', 'Стоимость обучения, скидки и кредит 3%'),
    ('Общежитие и студенческий городок', 'Общежитие и студенческий городок'),
    ('Перевод из другого вуза / восстановление', 'Перевод из другого вуза / восстановление'),
    ('Целевое обучение и льготные квоты', 'Целевое обучение и льготные квоты'),
    ('Другой вопрос', 'Другой вопрос'),
]

SPAM_KEYWORDS = [
    'casino', 'viagra', 'cryptocurrency', 'bitcoin', 'forex', 'dating', 
    'порно', 'казино', 'вулкан', 'ставки', 'проститутки', 'займ онлайн'
]


class FeedbackForm(forms.ModelForm):
    subject = forms.ChoiceField(
        choices=SUBJECT_CHOICES,
        label='Тема обращения',
        widget=forms.Select(attrs={
            'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 text-sm bg-slate-50 focus:bg-white focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all',
        })
    )

    consent = forms.BooleanField(
        required=True,
        label='Я даю согласие на обработку персональных данных',
        widget=forms.CheckboxInput(attrs={
            'class': 'w-4 h-4 rounded text-blue-600 focus:ring-blue-500 border-slate-300 mt-0.5',
        })
    )

    # Защита от спама 1: Honeypot-поле (скрыто от пользователей, роботы заполняют автоматически)
    website = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'hidden',
            'tabindex': '-1',
            'autocomplete': 'off',
            'aria-hidden': 'true',
        }),
        label=''
    )

    # Защита от спама 2: Простая контрольная капча (математический проверочный вопрос)
    captcha_answer = forms.CharField(
        required=True,
        label='Проверка: сколько будет 5 + 3?',
        widget=forms.TextInput(attrs={
            'placeholder': 'Укажите ответ (число)',
            'class': 'w-full px-4 py-2.5 rounded-xl border border-slate-200 text-sm bg-slate-50 focus:bg-white focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all',
        })
    )

    class Meta:
        model = FeedbackMessage
        fields = ['full_name', 'phone', 'email', 'subject', 'message']
        widgets = {
            'full_name': forms.TextInput(attrs={
                'placeholder': 'Например: Иванов Иван Иванович',
                'class': 'w-full pl-11 pr-4 py-3 rounded-xl border border-slate-200 text-sm bg-slate-50 focus:bg-white focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all',
            }),
            'phone': forms.TextInput(attrs={
                'placeholder': '+7 (999) 000-00-00',
                'class': 'w-full pl-11 pr-4 py-3 rounded-xl border border-slate-200 text-sm bg-slate-50 focus:bg-white focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all',
            }),
            'email': forms.EmailInput(attrs={
                'placeholder': 'applicant@example.ru',
                'class': 'w-full pl-11 pr-4 py-3 rounded-xl border border-slate-200 text-sm bg-slate-50 focus:bg-white focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all',
            }),
            'message': forms.Textarea(attrs={
                'rows': 5,
                'placeholder': 'Опишите ваш вопрос или ситуацию подробно...',
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 text-sm bg-slate-50 focus:bg-white focus:ring-2 focus:ring-blue-500 focus:outline-none transition-all resize-none',
            }),
        }

    def clean_website(self):
        # Honeypot: если поле заполнено, это спам-бот
        data = self.cleaned_data.get('website', '').strip()
        if data:
            raise ValidationError('Спам-активность обнаружена.')
        return data

    def clean_captcha_answer(self):
        answer = self.cleaned_data.get('captcha_answer', '').strip()
        if answer not in ['8', 'восемь', 'Eight', 'eight']:
            raise ValidationError('Неверный ответ на контрольный вопрос. Правильный ответ: 8.')
        return answer

    def clean_full_name(self):
        name = self.cleaned_data.get('full_name', '').strip()
        parts = name.split()
        if len(parts) < 2:
            raise ValidationError('Пожалуйста, укажите имя и фамилию (не менее 2 слов).')
        if any(char.isdigit() for char in name):
            raise ValidationError('ФИО не может содержать цифры.')
        return name

    def clean_phone(self):
        phone = self.cleaned_data.get('phone', '').strip()
        digits = re.sub(r'\D', '', phone)
        if len(digits) < 10 or len(digits) > 12:
            raise ValidationError('Укажите корректный номер телефона (от 10 до 11 цифр).')
        return phone

    def clean_message(self):
        message = self.cleaned_data.get('message', '').strip()
        if len(message) < 10:
            raise ValidationError('Сообщение слишком короткое (минимум 10 символов).')
        
        # Проверка на спам-ключевые слова
        msg_lower = message.lower()
        for kw in SPAM_KEYWORDS:
            if kw in msg_lower:
                raise ValidationError('Ваше сообщение содержит недопустимый контент или спам.')

        return message
