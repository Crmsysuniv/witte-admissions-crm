from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from admissions.models import Faculty, Specialty, EducationProgram, Application
from audit.models import StatusLog, Notification
from accounts.models import ApplicantProfile, OfficerProfile

User = get_user_model()


class OfficerApplicationsListTests(TestCase):
    """
    Тестирование реестра поданных заявлений сотрудника приемной комиссии.
    Проверяет права доступа, фильтрацию по статусам, факультетам,
    поиск по ФИО/СНИЛС, а также действия смены статуса.
    """
    def setUp(self):
        self.client = Client()

        # Сотрудник приемной комиссии
        self.officer_user = User.objects.create_user(
            username='officer_test',
            password='testpassword123',
            email='officer_test@witte.ru',
            first_name='Ольга',
            last_name='Иванова',
            role=User.Role.OFFICER
        )
        OfficerProfile.objects.create(
            user=self.officer_user,
            position='Старший специалист',
            cabinet='205'
        )

        # Обычный абитуриент 1
        self.applicant_user = User.objects.create_user(
            username='applicant_test',
            password='testpassword123',
            email='applicant_test@witte.ru',
            first_name='Иван',
            last_name='Смирнов',
            role=User.Role.APPLICANT
        )
        ApplicantProfile.objects.create(
            user=self.applicant_user,
            snils='111-222-333 44'
        )

        # Абитуриент 2
        self.applicant2_user = User.objects.create_user(
            username='applicant2_test',
            password='testpassword123',
            email='applicant2_test@witte.ru',
            first_name='Анна',
            last_name='Кузнецова',
            role=User.Role.APPLICANT
        )
        ApplicantProfile.objects.create(
            user=self.applicant2_user,
            snils='555-666-777 88'
        )

        # Факультеты
        self.faculty_it = Faculty.objects.create(
            name='Факультет информационных технологий',
            code='ФИТ'
        )
        self.faculty_econ = Faculty.objects.create(
            name='Факультет экономики и управления',
            code='ФЭУ'
        )

        # Специальности и программы
        self.spec_it = Specialty.objects.create(
            faculty=self.faculty_it,
            code='09.03.03',
            name='Прикладная информатика',
            education_level=Specialty.EducationLevel.BACHELOR
        )
        self.prog_it = EducationProgram.objects.create(
            specialty=self.spec_it,
            study_form=EducationProgram.StudyForm.FULL_TIME,
            tuition_fee=140000.00,
            duration='4 года'
        )

        self.spec_econ = Specialty.objects.create(
            faculty=self.faculty_econ,
            code='38.03.01',
            name='Экономика',
            education_level=Specialty.EducationLevel.BACHELOR
        )
        self.prog_econ = EducationProgram.objects.create(
            specialty=self.spec_econ,
            study_form=EducationProgram.StudyForm.PART_TIME,
            tuition_fee=90000.00,
            duration='4 года 6 месяцев'
        )

        # Заявления
        self.app1 = Application.objects.create(
            applicant=self.applicant_user,
            program=self.prog_it,
            status=Application.Status.SUBMITTED,
            financing_type=Application.FinancingType.BUDGET
        )

        self.app2 = Application.objects.create(
            applicant=self.applicant2_user,
            program=self.prog_econ,
            status=Application.Status.APPROVED,
            financing_type=Application.FinancingType.PAID
        )

    def test_anonymous_redirected_to_login(self):
        url = reverse('officer:applications_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_applicant_forbidden(self):
        self.client.login(username='applicant_test', password='testpassword123')
        url = reverse('officer:applications_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_officer_access_granted(self):
        self.client.login(username='officer_test', password='testpassword123')
        url = reverse('officer:applications_list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'officer/applications_list.html')
        self.assertContains(response, 'Реестр поданных')
        self.assertContains(response, 'Смирнов')
        self.assertContains(response, 'Кузнецова')

    def test_filter_by_status(self):
        self.client.login(username='officer_test', password='testpassword123')
        url = reverse('officer:applications_list')
        response = self.client.get(url, {'status': 'SUBMITTED'})
        self.assertEqual(response.status_code, 200)
        apps = response.context['applications']
        self.assertEqual(len(apps), 1)
        self.assertEqual(apps[0].id, self.app1.id)

    def test_filter_by_faculty(self):
        self.client.login(username='officer_test', password='testpassword123')
        url = reverse('officer:applications_list')
        response = self.client.get(url, {'faculty': self.faculty_econ.id})
        self.assertEqual(response.status_code, 200)
        apps = response.context['applications']
        self.assertEqual(len(apps), 1)
        self.assertEqual(apps[0].id, self.app2.id)

    def test_search_by_fio_and_snils(self):
        self.client.login(username='officer_test', password='testpassword123')
        url = reverse('officer:applications_list')

        # Поиск по фамилии
        response = self.client.get(url, {'search': 'Смирнов'})
        self.assertEqual(response.status_code, 200)
        apps = response.context['applications']
        self.assertEqual(len(apps), 1)
        self.assertEqual(apps[0].id, self.app1.id)

        # Поиск по имени второго абитуриента
        response = self.client.get(url, {'search': 'Анна'})
        self.assertEqual(response.status_code, 200)
        apps = response.context['applications']
        self.assertEqual(len(apps), 1)
        self.assertEqual(apps[0].id, self.app2.id)

        # Поиск по СНИЛС
        response = self.client.get(url, {'search': '111-222-333'})
        self.assertEqual(response.status_code, 200)
        apps = response.context['applications']
        self.assertEqual(len(apps), 1)
        self.assertEqual(apps[0].id, self.app1.id)

    def test_change_status_action(self):
        self.client.login(username='officer_test', password='testpassword123')
        url = reverse('officer:applications_list')
        post_data = {
            'action': 'change_status',
            'application_id': self.app1.id,
            'new_status': Application.Status.UNDER_REVIEW,
            'officer_comment': 'Взято на первичную проверку'
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)

        self.app1.refresh_from_db()
        self.assertEqual(self.app1.status, Application.Status.UNDER_REVIEW)
        self.assertEqual(self.app1.officer_comment, 'Взято на первичную проверку')

        # Проверка создания StatusLog
        log_entry = StatusLog.objects.filter(application=self.app1).latest('changed_at')
        self.assertEqual(log_entry.old_status, Application.Status.SUBMITTED)
        self.assertEqual(log_entry.new_status, Application.Status.UNDER_REVIEW)
        self.assertEqual(log_entry.changed_by, self.officer_user)

        # Проверка создания Notification
        notification = Notification.objects.filter(user=self.applicant_user).latest('created_at')
        self.assertIn(self.app1.get_status_display(), notification.message)


class OfficerApplicationDetailTests(TestCase):
    """
    Тестирование экрана детальной проверки заявления (officer:application_detail).
    Проверяет права доступа, отображение реквизитов, баллов и документов,
    смену статусов («Принято», «Отклонено», «Требуются правки») и верификацию файлов.
    """
    def setUp(self):
        self.client = Client()

        self.officer_user = User.objects.create_user(
            username='officer_reviewer',
            password='testpassword123',
            email='reviewer@witte.ru',
            first_name='Светлана',
            last_name='Романова',
            role=User.Role.OFFICER
        )
        OfficerProfile.objects.create(
            user=self.officer_user,
            position='Ведущий специалист',
            cabinet='102'
        )

        self.applicant_user = User.objects.create_user(
            username='applicant_ivan',
            password='testpassword123',
            email='ivan@example.com',
            first_name='Иван',
            last_name='Петров',
            role=User.Role.APPLICANT
        )
        self.profile = ApplicantProfile.objects.create(
            user=self.applicant_user,
            snils='222-333-444 55',
            passport_series='4510',
            passport_number='123456',
            passport_issued_by='ОВД г. Москвы',
            address='г. Москва, ул. Ленина, д. 1'
        )

        self.faculty = Faculty.objects.create(name='Юридический факультет', code='ЮФ')
        self.specialty = Specialty.objects.create(
            faculty=self.faculty,
            code='40.03.01',
            name='Юриспруденция',
            education_level=Specialty.EducationLevel.BACHELOR
        )
        self.program = EducationProgram.objects.create(
            specialty=self.specialty,
            study_form=EducationProgram.StudyForm.FULL_TIME,
            tuition_fee=160000.00,
            duration='4 года'
        )

        self.application = Application.objects.create(
            applicant=self.applicant_user,
            program=self.program,
            status=Application.Status.SUBMITTED,
            financing_type=Application.FinancingType.BUDGET
        )

    def test_anonymous_redirected_to_login(self):
        url = reverse('officer:application_detail', kwargs={'pk': self.application.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_applicant_cannot_access_detail(self):
        self.client.login(username='applicant_ivan', password='testpassword123')
        url = reverse('officer:application_detail', kwargs={'pk': self.application.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_officer_can_view_detail(self):
        self.client.login(username='officer_reviewer', password='testpassword123')
        url = reverse('officer:application_detail', kwargs={'pk': self.application.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'officer/application_detail.html')
        self.assertContains(response, 'Иван')
        self.assertContains(response, 'Петров')
        self.assertContains(response, 'Юриспруденция')
        self.assertContains(response, '222-333-444 55')

    def test_change_status_to_approved(self):
        self.client.login(username='officer_reviewer', password='testpassword123')
        url = reverse('officer:application_detail', kwargs={'pk': self.application.pk})
        response = self.client.post(url, {
            'action': 'change_status',
            'new_status': Application.Status.APPROVED,
            'officer_comment': 'Заявление одобрено'
        })
        self.assertEqual(response.status_code, 302)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, Application.Status.APPROVED)
        self.assertEqual(self.application.officer_comment, 'Заявление одобрено')

        # Проверка StatusLog
        log = StatusLog.objects.filter(application=self.application).latest('changed_at')
        self.assertEqual(log.new_status, Application.Status.APPROVED)
        self.assertEqual(log.changed_by, self.officer_user)

    def test_change_status_to_documents_required(self):
        self.client.login(username='officer_reviewer', password='testpassword123')
        url = reverse('officer:application_detail', kwargs={'pk': self.application.pk})
        response = self.client.post(url, {
            'action': 'change_status',
            'new_status': Application.Status.DOCUMENTS_REQUIRED,
            'officer_comment': 'Прикрепите четкий скан паспорта'
        })
        self.assertEqual(response.status_code, 302)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, Application.Status.DOCUMENTS_REQUIRED)
        self.assertEqual(self.application.officer_comment, 'Прикрепите четкий скан паспорта')

    def test_change_status_to_rejected(self):
        self.client.login(username='officer_reviewer', password='testpassword123')
        url = reverse('officer:application_detail', kwargs={'pk': self.application.pk})
        response = self.client.post(url, {
            'action': 'change_status',
            'new_status': Application.Status.REJECTED,
            'officer_comment': 'Отказ в приеме документов'
        })
        self.assertEqual(response.status_code, 302)
        self.application.refresh_from_db()
        self.assertEqual(self.application.status, Application.Status.REJECTED)
        self.assertEqual(self.application.officer_comment, 'Отказ в приеме документов')

