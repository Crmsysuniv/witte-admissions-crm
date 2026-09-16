from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from admissions.models import Faculty, Specialty, EducationProgram, ExamSubject, Application, ApplicationDocument, ExamScore
from audit.models import StatusLog, Notification
from accounts.models import ApplicantProfile, OfficerProfile
from feedback.models import FeedbackMessage

User = get_user_model()


class AdminDashboardTests(TestCase):
    """
    Тестирование главного аналитического дашборда руководителя (admin/dashboard.html).
    Проверяет:
    - Разграничение прав доступа (анонимные, абитуриенты, сотрудники, администраторы)
    - Корректность расчета ключевых KPI (всего заявлений, бюджет/платка, конверсия воронки)
    - Наличие сводных таблиц по факультетам и направлениям
    - Генерацию контекста графиков (JSON)
    """
    def setUp(self):
        self.client = Client()

        # Администратор
        self.admin_user = User.objects.create_user(
            username='admin_exec',
            password='testpassword123',
            email='admin@witte.ru',
            first_name='Алексей',
            last_name='Ректоров',
            role=User.Role.ADMIN
        )

        # Обычный сотрудник приемной комиссии (без прав администратора)
        self.officer_user = User.objects.create_user(
            username='officer_plain',
            password='testpassword123',
            email='officer@witte.ru',
            first_name='Ольга',
            last_name='Инспекторова',
            role=User.Role.OFFICER
        )

        # Абитуриент 1
        self.applicant1 = User.objects.create_user(
            username='applicant_one',
            password='testpassword123',
            email='app1@example.com',
            first_name='Иван',
            last_name='Петров',
            role=User.Role.APPLICANT
        )
        ApplicantProfile.objects.create(user=self.applicant1, snils='111-222-333 44')

        # Абитуриент 2
        self.applicant2 = User.objects.create_user(
            username='applicant_two',
            password='testpassword123',
            email='app2@example.com',
            first_name='Мария',
            last_name='Сидорова',
            role=User.Role.APPLICANT
        )
        ApplicantProfile.objects.create(user=self.applicant2, snils='555-666-777 88')

        # Факультет и специальности
        self.faculty = Faculty.objects.create(name='Факультет информационных технологий', code='ФИТ')
        self.specialty = Specialty.objects.create(
            faculty=self.faculty,
            code='09.03.03',
            name='Прикладная информатика',
            education_level=Specialty.EducationLevel.BACHELOR,
            budget_places=10,
            paid_places=20
        )
        self.program = EducationProgram.objects.create(
            specialty=self.specialty,
            study_form=EducationProgram.StudyForm.FULL_TIME,
            tuition_fee=150000.00,
            duration='4 года'
        )

        # Заявления
        self.app1 = Application.objects.create(
            applicant=self.applicant1,
            program=self.program,
            status=Application.Status.APPROVED,
            financing_type=Application.FinancingType.BUDGET
        )

        self.app2 = Application.objects.create(
            applicant=self.applicant2,
            program=self.program,
            status=Application.Status.ENROLLED,
            financing_type=Application.FinancingType.PAID
        )

        # Обратная связь
        FeedbackMessage.objects.create(
            full_name='Тестовый Гражданин',
            email='feedback@example.com',
            phone='+7 999 123-45-67',
            subject='Вопрос по поступлению',
            message='Здравствуйте! Подскажите проходной балл.',
            status=FeedbackMessage.Status.NEW
        )

    def test_anonymous_redirected_to_login(self):
        url = reverse('admin_dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_applicant_forbidden(self):
        self.client.login(username='applicant_one', password='testpassword123')
        url = reverse('admin_dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_officer_without_admin_forbidden(self):
        self.client.login(username='officer_plain', password='testpassword123')
        url = reverse('admin_dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_admin_access_granted(self):
        self.client.login(username='admin_exec', password='testpassword123')
        url = reverse('admin_dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/dashboard.html')

        # Проверка контекста
        self.assertEqual(response.context['total_applications'], 2)
        self.assertEqual(response.context['budget_stats']['applications'], 1)
        self.assertEqual(response.context['paid_stats']['applications'], 1)
        self.assertEqual(response.context['paid_stats']['enrolled'], 1)
        self.assertGreater(response.context['funnel']['overall_conversion'], 0)
        self.assertIn('charts_json', response.context)

        # Проверка контента на странице
        self.assertContains(response, 'Главный аналитический дашборд')
        self.assertContains(response, 'Прикладная информатика')
        self.assertContains(response, 'Факультет информационных технологий')
        self.assertContains(response, 'Сквозная воронка конверсии')
        self.assertContains(response, 'Бюджетные места')
        self.assertContains(response, 'Платные места (Договор)')

    def test_superuser_access_granted(self):
        superuser = User.objects.create_superuser(
            username='superuser_admin',
            password='testpassword123',
            email='root_admin@witte.ru'
        )
        self.client.login(username='superuser_admin', password='testpassword123')
        url = reverse('admin_dashboard')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

