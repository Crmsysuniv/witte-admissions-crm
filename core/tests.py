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

        import json
        charts_data = json.loads(response.context['charts_json'])
        self.assertIn('faculty_bar', charts_data)
        self.assertIn('labels', charts_data['faculty_bar'])
        self.assertIn('total', charts_data['faculty_bar'])
        self.assertIn('study_forms_pie', charts_data)
        self.assertIn('labels', charts_data['study_forms_pie'])
        self.assertIn('data', charts_data['study_forms_pie'])

        # Проверка контента на странице
        self.assertContains(response, 'Главный аналитический дашборд')
        self.assertContains(response, 'Прикладная информатика')
        self.assertContains(response, 'Факультет информационных технологий')
        self.assertContains(response, 'Сквозная воронка конверсии')
        self.assertContains(response, 'Бюджетные места')
        self.assertContains(response, 'Платные места (Договор)')
        self.assertContains(response, 'facultyBarChart')
        self.assertContains(response, 'studyFormsPieChart')
        self.assertContains(response, 'timelineChart')

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


class AdminUsersListTests(TestCase):
    """
    Тестирование страницы управления учетными записями и назначения ролей (admin/users_list.html).
    Проверяет:
    - Разграничение прав доступа (анонимные, абитуриенты, сотрудники, администраторы)
    - Полнотекстовый поиск и фильтрацию по ролям и активности
    - Изменение ролей пользователей (назначение сотрудником, администратором, абитуриентом)
    - Блокировку и активацию учетных записей с защитой от самоблокировки
    - Пагинацию и корректность отображения контекста
    """
    def setUp(self):
        self.client = Client()

        # Администратор
        self.admin_user = User.objects.create_user(
            username='admin_boss',
            password='testpassword123',
            email='boss@witte.ru',
            first_name='Сергей',
            last_name='Администраторов',
            role=User.Role.ADMIN
        )

        # Офицер
        self.officer_user = User.objects.create_user(
            username='officer_katya',
            password='testpassword123',
            email='katya@witte.ru',
            first_name='Екатерина',
            last_name='Приемная',
            role=User.Role.OFFICER
        )
        OfficerProfile.objects.create(user=self.officer_user, position='Секретарь ПК', cabinet='102')

        # Абитуриент
        self.applicant = User.objects.create_user(
            username='applicant_dima',
            password='testpassword123',
            email='dima@example.com',
            first_name='Дмитрий',
            last_name='Школьников',
            role=User.Role.APPLICANT
        )
        ApplicantProfile.objects.create(user=self.applicant, snils='999-888-777 00')

    def test_anonymous_redirected_to_login(self):
        url = reverse('admin_users_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_applicant_forbidden(self):
        self.client.login(username='applicant_dima', password='testpassword123')
        url = reverse('admin_users_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_officer_forbidden(self):
        self.client.login(username='officer_katya', password='testpassword123')
        url = reverse('admin_users_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_admin_access_and_render(self):
        self.client.login(username='admin_boss', password='testpassword123')
        url = reverse('admin_users_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/users_list.html')

        # Проверка контекста
        self.assertEqual(response.context['kpi']['total'], 3)
        self.assertEqual(response.context['kpi']['admin'], 1)
        self.assertEqual(response.context['kpi']['officer'], 1)
        self.assertEqual(response.context['kpi']['applicant'], 1)

        # Проверка наличия элементов на странице
        self.assertContains(response, 'Управление учетными записями')
        self.assertContains(response, 'admin_boss')
        self.assertContains(response, 'officer_katya')
        self.assertContains(response, 'applicant_dima')
        self.assertContains(response, '999-888-777 00')

    def test_search_and_filter(self):
        self.client.login(username='admin_boss', password='testpassword123')
        
        # Поиск по СНИЛС
        response = self.client.get(reverse('admin_users_list') + '?q=999-888')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['kpi']['filtered'], 1)
        self.assertContains(response, 'applicant_dima')
        self.assertNotContains(response, 'officer_katya')

        # Фильтр по роли
        response = self.client.get(reverse('admin_users_list') + '?role=OFFICER')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['kpi']['filtered'], 1)
        self.assertContains(response, 'officer_katya')
        self.assertNotContains(response, 'applicant_dima')

    def test_update_role_action(self):
        self.client.login(username='admin_boss', password='testpassword123')
        url = reverse('admin_users_list')

        # Повышение абитуриента до сотрудника комиссии с указанием должности и кабинета
        post_data = {
            'action': 'update_role',
            'user_id': self.applicant.id,
            'new_role': User.Role.OFFICER,
            'officer_position': 'Старший секретарь ПК',
            'officer_cabinet': 'Главный кампус, каб. 204',
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)

        self.applicant.refresh_from_db()
        self.assertEqual(self.applicant.role, User.Role.OFFICER)
        self.assertTrue(self.applicant.is_staff)
        self.assertTrue(OfficerProfile.objects.filter(user=self.applicant).exists())
        self.assertEqual(self.applicant.officer_profile.position, 'Старший секретарь ПК')
        self.assertEqual(self.applicant.officer_profile.cabinet, 'Главный кампус, каб. 204')

        # Проверка создания уведомления
        self.assertTrue(Notification.objects.filter(user=self.applicant).exists())

    def test_revoke_role_to_applicant(self):
        self.client.login(username='admin_boss', password='testpassword123')
        url = reverse('admin_users_list')

        # Снятие прав сотрудника комиссии
        post_data = {
            'action': 'update_role',
            'user_id': self.officer_user.id,
            'new_role': User.Role.APPLICANT,
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)

        self.officer_user.refresh_from_db()
        self.assertEqual(self.officer_user.role, User.Role.APPLICANT)
        self.assertFalse(self.officer_user.is_staff)

    def test_prevent_self_demotion(self):
        self.client.login(username='admin_boss', password='testpassword123')
        url = reverse('admin_users_list')

        # Попытка понизить роль самого себя
        post_data = {
            'action': 'update_role',
            'user_id': self.admin_user.id,
            'new_role': User.Role.APPLICANT,
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)

        self.admin_user.refresh_from_db()
        self.assertEqual(self.admin_user.role, User.Role.ADMIN)

    def test_toggle_active_action(self):
        self.client.login(username='admin_boss', password='testpassword123')
        url = reverse('admin_users_list')

        # Блокировка абитуриента
        post_data = {
            'action': 'toggle_active',
            'user_id': self.applicant.id,
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)

        self.applicant.refresh_from_db()
        self.assertFalse(self.applicant.is_active)

        # Разблокировка
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)

        self.applicant.refresh_from_db()
        self.assertTrue(self.applicant.is_active)

    def test_prevent_self_deactivation(self):
        self.client.login(username='admin_boss', password='testpassword123')
        url = reverse('admin_users_list')

        # Попытка заблокировать самого себя
        post_data = {
            'action': 'toggle_active',
            'user_id': self.admin_user.id,
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)

        self.admin_user.refresh_from_db()
        self.assertTrue(self.admin_user.is_active)


class AdminSpecialtiesManageTests(TestCase):
    """
    Тестирование страницы управления направлениями подготовки и квотами КЦП (admin/specialties_manage.html).
    """
    def setUp(self):
        self.client = Client()

        # Администратор
        self.admin = User.objects.create_user(
            username='admin_kcp',
            password='testpassword123',
            email='kcp@witte.ru',
            role=User.Role.ADMIN
        )

        # Факультет
        self.faculty = Faculty.objects.create(name='Факультет экономики', code='ФЭК')

        # Специальность
        self.specialty = Specialty.objects.create(
            faculty=self.faculty,
            code='38.03.01',
            name='Экономика предприятий',
            education_level=Specialty.EducationLevel.BACHELOR,
            budget_places=15,
            paid_places=30,
            is_active=True
        )

        self.program = EducationProgram.objects.create(
            specialty=self.specialty,
            study_form=EducationProgram.StudyForm.FULL_TIME,
            tuition_fee=165000.00,
            duration='4 года',
            is_active=True
        )

    def test_admin_access_and_render(self):
        self.client.login(username='admin_kcp', password='testpassword123')
        url = reverse('admin_specialties_manage')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'admin/specialties_manage.html')
        self.assertContains(response, '38.03.01')
        self.assertContains(response, 'Экономика предприятий')
        self.assertContains(response, 'Факультет экономики')
        self.assertEqual(response.context['kpi']['total_specialties'], 1)
        self.assertEqual(response.context['kpi']['total_budget'], 15)
        self.assertEqual(response.context['kpi']['total_paid'], 30)

    def test_create_specialty_action(self):
        self.client.login(username='admin_kcp', password='testpassword123')
        url = reverse('admin_specialties_manage')

        post_data = {
            'action': 'create_specialty',
            'faculty': self.faculty.id,
            'code': '38.03.02',
            'name': 'Менеджмент и маркетинг',
            'education_level': Specialty.EducationLevel.BACHELOR,
            'budget_places': 10,
            'paid_places': 40,
            'is_active': '1',
            'initial_study_form': EducationProgram.StudyForm.FULL_TIME,
            'initial_tuition_fee': 170000,
            'initial_duration': '4 года',
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)

        self.assertTrue(Specialty.objects.filter(code='38.03.02').exists())
        new_sp = Specialty.objects.get(code='38.03.02')
        self.assertEqual(new_sp.budget_places, 10)
        self.assertEqual(new_sp.paid_places, 40)
        self.assertTrue(new_sp.programs.filter(study_form=EducationProgram.StudyForm.FULL_TIME).exists())

    def test_edit_specialty_action(self):
        self.client.login(username='admin_kcp', password='testpassword123')
        url = reverse('admin_specialties_manage')

        post_data = {
            'action': 'edit_specialty',
            'specialty_id': self.specialty.id,
            'faculty': self.faculty.id,
            'code': '38.03.01',
            'name': 'Экономика и финансы (обновлено)',
            'education_level': Specialty.EducationLevel.BACHELOR,
            'budget_places': 20,
            'paid_places': 35,
            'is_active': '1',
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)

        self.specialty.refresh_from_db()
        self.assertEqual(self.specialty.name, 'Экономика и финансы (обновлено)')
        self.assertEqual(self.specialty.budget_places, 20)

    def test_add_program_action(self):
        self.client.login(username='admin_kcp', password='testpassword123')
        url = reverse('admin_specialties_manage')

        post_data = {
            'action': 'add_program',
            'specialty_id': self.specialty.id,
            'study_form': EducationProgram.StudyForm.PART_TIME,
            'tuition_fee': 95000,
            'duration': '4 года 6 месяцев',
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)

        self.assertTrue(self.specialty.programs.filter(study_form=EducationProgram.StudyForm.PART_TIME).exists())




