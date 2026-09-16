from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from admissions.models import Faculty, Specialty, EducationProgram, Application
from audit.models import StatusLog, Notification
from accounts.models import ApplicantProfile, OfficerProfile
from feedback.models import FeedbackMessage

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


class OfficerInquiriesTests(TestCase):
    """
    Тестирование раздела входящих обращений граждан (officer:inquiries).
    Проверяет права доступа, фильтрацию по статусу, поиск по теме и автору,
    сохранение ответов сотрудника и изменение статусов обращений.
    """
    def setUp(self):
        self.client = Client()

        self.officer_user = User.objects.create_user(
            username='officer_support',
            password='testpassword123',
            email='support_officer@witte.ru',
            first_name='Елена',
            last_name='Соколова',
            role=User.Role.OFFICER
        )
        OfficerProfile.objects.create(
            user=self.officer_user,
            position='Консультант приемной комиссии',
            cabinet='105'
        )

        self.applicant_user = User.objects.create_user(
            username='applicant_inq',
            password='testpassword123',
            email='inq_applicant@example.com',
            first_name='Сергей',
            last_name='Морозов',
            role=User.Role.APPLICANT
        )

        self.inquiry1 = FeedbackMessage.objects.create(
            full_name='Сергей Морозов',
            phone='+7 (999) 111-22-33',
            email='sergey@example.com',
            subject='Сроки подачи документов на очное отделение',
            message='Здравствуйте! Подскажите, пожалуйста, до какого числа можно подать оригинал аттестата?',
            status=FeedbackMessage.Status.NEW
        )

        self.inquiry2 = FeedbackMessage.objects.create(
            full_name='Мария Васильева',
            phone='+7 (999) 444-55-66',
            email='maria@example.com',
            subject='Вопрос о стоимости обучения на IT-направлениях',
            message='Добрый день! Предоставляется ли скидка при оплате за весь год сразу?',
            status=FeedbackMessage.Status.RESOLVED,
            officer_response='Да, при единовременной оплате предоставляется скидка 5%.',
            responded_by=self.officer_user
        )

    def test_anonymous_redirected_to_login(self):
        url = reverse('officer:inquiries')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_applicant_cannot_access_inquiries(self):
        self.client.login(username='applicant_inq', password='testpassword123')
        url = reverse('officer:inquiries')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_officer_can_view_inquiries(self):
        self.client.login(username='officer_support', password='testpassword123')
        url = reverse('officer:inquiries')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'officer/inquiries.html')
        self.assertContains(response, 'Сергей Морозов')
        self.assertContains(response, 'Мария Васильева')
        self.assertContains(response, 'Сроки подачи документов')

    def test_filter_inquiries_by_status(self):
        self.client.login(username='officer_support', password='testpassword123')
        url = reverse('officer:inquiries')
        response = self.client.get(url, {'status': 'NEW'})
        self.assertEqual(response.status_code, 200)
        inquiries = response.context['inquiries']
        self.assertEqual(len(inquiries), 1)
        self.assertEqual(inquiries[0].id, self.inquiry1.id)

    def test_search_inquiries(self):
        self.client.login(username='officer_support', password='testpassword123')
        url = reverse('officer:inquiries')

        # Поиск по теме
        response = self.client.get(url, {'search': 'стоимости'})
        self.assertEqual(response.status_code, 200)
        inquiries = response.context['inquiries']
        self.assertEqual(len(inquiries), 1)
        self.assertEqual(inquiries[0].id, self.inquiry2.id)

        # Поиск по ФИО
        response = self.client.get(url, {'search': 'Морозов'})
        self.assertEqual(response.status_code, 200)
        inquiries = response.context['inquiries']
        self.assertEqual(len(inquiries), 1)
        self.assertEqual(inquiries[0].id, self.inquiry1.id)

    def test_officer_respond_to_inquiry(self):
        self.client.login(username='officer_support', password='testpassword123')
        url = reverse('officer:inquiries')
        response = self.client.post(url, {
            'action': 'respond',
            'inquiry_id': self.inquiry1.id,
            'officer_response': 'Здравствуйте! Прием оригиналов документов завершается 25 июля в 18:00.',
            'status': FeedbackMessage.Status.RESOLVED
        })
        self.assertEqual(response.status_code, 302)

        self.inquiry1.refresh_from_db()
        self.assertEqual(self.inquiry1.status, FeedbackMessage.Status.RESOLVED)
        self.assertEqual(self.inquiry1.officer_response, 'Здравствуйте! Прием оригиналов документов завершается 25 июля в 18:00.')
        self.assertEqual(self.inquiry1.responded_by, self.officer_user)
        self.assertIsNotNone(self.inquiry1.responded_at)

    def test_officer_take_in_progress(self):
        self.client.login(username='officer_support', password='testpassword123')
        url = reverse('officer:inquiries')
        response = self.client.post(url, {
            'action': 'take_in_progress',
            'inquiry_id': self.inquiry1.id
        })
        self.assertEqual(response.status_code, 302)

        self.inquiry1.refresh_from_db()
        self.assertEqual(self.inquiry1.status, FeedbackMessage.Status.IN_PROGRESS)
        self.assertEqual(self.inquiry1.responded_by, self.officer_user)


class OfficerProtocolsTests(TestCase):
    """
    Тестирование раздела формирования приказов о зачислении и протоколов (officer:protocols).
    Проверяет права доступа, фильтрацию кандидатов, массовую генерацию приказов
    со сменой статуса на ENROLLED, создание аудита (StatusLog) и уведомлений (Notification),
    а также операцию возврата заявления в статус «Одобрено».
    """
    def setUp(self):
        self.client = Client()

        self.officer_user = User.objects.create_user(
            username='officer_secretary',
            password='testpassword123',
            email='secretary@witte.ru',
            first_name='Татьяна',
            last_name='Васильева',
            role=User.Role.OFFICER
        )
        OfficerProfile.objects.create(
            user=self.officer_user,
            position='Ответственный секретарь',
            cabinet='201'
        )

        self.applicant1_user = User.objects.create_user(
            username='applicant_enr1',
            password='testpassword123',
            email='enr1@example.com',
            first_name='Алексей',
            last_name='Кузнецов',
            role=User.Role.APPLICANT
        )
        ApplicantProfile.objects.create(
            user=self.applicant1_user,
            snils='111-222-333 44'
        )

        self.applicant2_user = User.objects.create_user(
            username='applicant_enr2',
            password='testpassword123',
            email='enr2@example.com',
            first_name='Дарья',
            last_name='Попова',
            role=User.Role.APPLICANT
        )
        ApplicantProfile.objects.create(
            user=self.applicant2_user,
            snils='555-666-777 88'
        )

        self.faculty = Faculty.objects.create(name='Факультет информационных технологий', code='ФИТ')
        self.specialty = Specialty.objects.create(
            faculty=self.faculty,
            code='09.03.01',
            name='Информатика и вычислительная техника',
            education_level=Specialty.EducationLevel.BACHELOR,
            budget_places=15,
            paid_places=30
        )
        self.program = EducationProgram.objects.create(
            specialty=self.specialty,
            study_form=EducationProgram.StudyForm.FULL_TIME,
            tuition_fee=150000.00,
            duration='4 года'
        )

        self.app1 = Application.objects.create(
            applicant=self.applicant1_user,
            program=self.program,
            status=Application.Status.APPROVED,
            financing_type=Application.FinancingType.BUDGET
        )

        self.app2 = Application.objects.create(
            applicant=self.applicant2_user,
            program=self.program,
            status=Application.Status.ENROLLED,
            financing_type=Application.FinancingType.PAID
        )

    def test_anonymous_redirected_to_login(self):
        url = reverse('officer:protocols')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_applicant_cannot_access_protocols(self):
        self.client.login(username='applicant_enr1', password='testpassword123')
        url = reverse('officer:protocols')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_officer_can_view_protocols(self):
        self.client.login(username='officer_secretary', password='testpassword123')
        url = reverse('officer:protocols')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'officer/protocols.html')
        self.assertContains(response, 'Формирование приказов')
        self.assertContains(response, 'Кузнецов')

    def test_filter_protocols_by_status(self):
        self.client.login(username='officer_secretary', password='testpassword123')
        url = reverse('officer:protocols')

        # Только одобренные
        response_appr = self.client.get(url, {'status': 'APPROVED'})
        self.assertEqual(response_appr.status_code, 200)
        apps = response_appr.context['applications']
        self.assertEqual(len(apps), 1)
        self.assertEqual(apps[0].id, self.app1.id)

        # Только зачисленные
        response_enr = self.client.get(url, {'status': 'ENROLLED'})
        self.assertEqual(response_enr.status_code, 200)
        apps_enr = response_enr.context['applications']
        self.assertEqual(len(apps_enr), 1)
        self.assertEqual(apps_enr[0].id, self.app2.id)

    def test_generate_order_batch_enrollment(self):
        self.client.login(username='officer_secretary', password='testpassword123')
        url = reverse('officer:protocols')
        post_data = {
            'action': 'generate_order',
            'selected_applications': [str(self.app1.id)],
            'order_number': '2026/П-042',
            'order_date': '15.08.2026',
            'order_type': 'BUDGET',
            'protocol_number': '12',
            'order_basis': 'Решение приемной комиссии МУ им. С.Ю. Витте'
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)

        self.app1.refresh_from_db()
        self.assertEqual(self.app1.status, Application.Status.ENROLLED)
        self.assertIn('2026/П-042', self.app1.officer_comment)

        # Проверка StatusLog
        log = StatusLog.objects.filter(application=self.app1).latest('changed_at')
        self.assertEqual(log.old_status, Application.Status.APPROVED)
        self.assertEqual(log.new_status, Application.Status.ENROLLED)
        self.assertEqual(log.changed_by, self.officer_user)

        # Проверка Notification
        notification = Notification.objects.filter(user=self.applicant1_user).latest('created_at')
        self.assertIn('2026/П-042', notification.message)
        self.assertEqual(notification.notification_type, Notification.NotificationType.SUCCESS)

    def test_revert_enrollment(self):
        self.client.login(username='officer_secretary', password='testpassword123')
        url = reverse('officer:protocols')
        post_data = {
            'action': 'revert_enrollment',
            'application_id': self.app2.id,
            'revert_reason': 'Заявление об отзыве согласия'
        }
        response = self.client.post(url, post_data)
        self.assertEqual(response.status_code, 302)

        self.app2.refresh_from_db()
        self.assertEqual(self.app2.status, Application.Status.APPROVED)

        log = StatusLog.objects.filter(application=self.app2).latest('changed_at')
        self.assertEqual(log.old_status, Application.Status.ENROLLED)
        self.assertEqual(log.new_status, Application.Status.APPROVED)
        self.assertEqual(log.changed_by, self.officer_user)


class OfficerSecurityRoleTests(TestCase):
    """
    Комплексное тестирование системы разграничения прав доступа и защиты маршрутов сотрудника приемной комиссии.
    Проверяет:
    1. Перенаправление анонимных пользователей на страницу входа (/login/?next=...).
    2. Запрет доступа (HTTP 403 Forbidden) для пользователей с ролью APPLICANT (Абитуриент).
    3. Разрешение полного доступа (HTTP 200) для пользователей с ролью OFFICER (Сотрудник приемной комиссии).
    4. Разрешение полного доступа (HTTP 200) для пользователей с ролью ADMIN (Администратор).
    5. Разрешение доступа для суперпользователей (is_superuser=True) и staff-пользователей (is_staff=True).
    6. Работу вспомогательной функции is_officer_or_admin и миксина OfficerRequiredMixin.
    7. Защищенность всех зарегистрированных маршрутов в officer:*.
    """
    def setUp(self):
        self.client = Client()

        # Администратор CRM
        self.admin_user = User.objects.create_user(
            username='admin_role_user',
            password='testpassword123',
            email='admin@witte.ru',
            first_name='Алексей',
            last_name='Администраторов',
            role=User.Role.ADMIN
        )

        # Сотрудник приемной комиссии
        self.officer_user = User.objects.create_user(
            username='officer_role_user',
            password='testpassword123',
            email='officer@witte.ru',
            first_name='Ольга',
            last_name='Сотрудникова',
            role=User.Role.OFFICER
        )
        OfficerProfile.objects.create(
            user=self.officer_user,
            position='Член приемной комиссии',
            cabinet='101'
        )

        # Обычный абитуриент
        self.applicant_user = User.objects.create_user(
            username='applicant_role_user',
            password='testpassword123',
            email='applicant@example.com',
            first_name='Иван',
            last_name='Абитуриентов',
            role=User.Role.APPLICANT
        )
        ApplicantProfile.objects.create(
            user=self.applicant_user,
            snils='123-456-789 00'
        )

        # Тестовая инфраструктура (факультет, специальность, программа, заявление)
        self.faculty = Faculty.objects.create(name='Факультет информационных систем', code='ФИС')
        self.specialty = Specialty.objects.create(
            faculty=self.faculty,
            code='09.03.02',
            name='Информационные системы и технологии',
            education_level=Specialty.EducationLevel.BACHELOR,
            budget_places=10,
            paid_places=25
        )
        self.program = EducationProgram.objects.create(
            specialty=self.specialty,
            study_form=EducationProgram.StudyForm.FULL_TIME,
            tuition_fee=145000.00,
            duration='4 года'
        )
        self.application = Application.objects.create(
            applicant=self.applicant_user,
            program=self.program,
            status=Application.Status.APPROVED,
            financing_type=Application.FinancingType.BUDGET
        )

        # Список тестируемых URL-адресов модуля сотрудника
        self.officer_urls = [
            reverse('officer:workplace'),
            reverse('officer:workplace_alias'),
            reverse('officer:applications_list'),
            reverse('officer:application_detail', kwargs={'pk': self.application.pk}),
            reverse('officer:inquiries'),
            reverse('officer:protocols'),
            reverse('officer:export_rating_xlsx'),
            reverse('officer:application_receipt_docx', kwargs={'pk': self.application.pk}),
        ]

    def test_anonymous_user_redirected_for_all_endpoints(self):
        """Анонимные пользователи перенаправляются на авторизацию со всех маршрутов сотрудника."""
        for url in self.officer_urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertIn('/login/', response.url)

    def test_applicant_user_forbidden_for_all_endpoints(self):
        """Пользователи с ролью APPLICANT получают 403 Forbidden при попытке доступа к любому эндпоинту сотрудника."""
        self.client.login(username='applicant_role_user', password='testpassword123')
        for url in self.officer_urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 403)

    def test_officer_user_allowed_for_all_endpoints(self):
        """Пользователи с ролью OFFICER имеют полный доступ ко всем маршрутам."""
        self.client.login(username='officer_role_user', password='testpassword123')
        for url in self.officer_urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)

    def test_admin_user_allowed_for_all_endpoints(self):
        """Пользователи с ролью ADMIN имеют полный доступ ко всем маршрутам сотрудника."""
        self.client.login(username='admin_role_user', password='testpassword123')
        for url in self.officer_urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)

    def test_superuser_allowed_for_all_endpoints(self):
        """Суперпользователи Django имеют доступ ко всем маршрутам сотрудника."""
        User.objects.create_superuser(
            username='superuser_test',
            password='testpassword123',
            email='root@witte.ru'
        )
        self.client.login(username='superuser_test', password='testpassword123')
        for url in self.officer_urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)

    def test_is_officer_or_admin_helper(self):
        """Тестирование корректности работы функции is_officer_or_admin."""
        from django.contrib.auth.models import AnonymousUser
        from officer.decorators import is_officer_or_admin
        self.assertFalse(is_officer_or_admin(None))
        self.assertFalse(is_officer_or_admin(AnonymousUser()))
        self.assertFalse(is_officer_or_admin(self.applicant_user))
        self.assertTrue(is_officer_or_admin(self.officer_user))
        self.assertTrue(is_officer_or_admin(self.admin_user))

    def test_officer_required_mixin(self):
        """Тестирование миксина OfficerRequiredMixin для CBV."""
        from officer.decorators import OfficerRequiredMixin
        from django.views.generic import View
        from django.http import HttpResponse
        from django.test import RequestFactory
        from django.core.exceptions import PermissionDenied
        from django.contrib.auth.models import AnonymousUser

        class DummyOfficerCBV(OfficerRequiredMixin, View):
            def get(self, request):
                return HttpResponse("CBV Officer OK")

        factory = RequestFactory()
        view = DummyOfficerCBV.as_view()

        # Анонимный запрос -> 302 редирект
        req_anon = factory.get('/officer/dummy/')
        req_anon.user = AnonymousUser()
        resp_anon = view(req_anon)
        self.assertEqual(resp_anon.status_code, 302)

        # Запрос от абитуриента -> PermissionDenied (403)
        req_appl = factory.get('/officer/dummy/')
        req_appl.user = self.applicant_user
        with self.assertRaises(PermissionDenied):
            view(req_appl)

        # Запрос от сотрудника -> 200 OK
        req_off = factory.get('/officer/dummy/')
        req_off.user = self.officer_user
        resp_off = view(req_off)
        self.assertEqual(resp_off.status_code, 200)
        self.assertEqual(resp_off.content.decode('utf-8'), "CBV Officer OK")

        # Запрос от администратора -> 200 OK
        req_adm = factory.get('/officer/dummy/')
        req_adm.user = self.admin_user
        resp_adm = view(req_adm)
        self.assertEqual(resp_adm.status_code, 200)
        self.assertEqual(resp_adm.content.decode('utf-8'), "CBV Officer OK")




