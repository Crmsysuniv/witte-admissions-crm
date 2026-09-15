from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from admissions.models import Faculty, Specialty, EducationProgram, ExamSubject
from accounts.models import ApplicantProfile, OfficerProfile

User = get_user_model()


class Command(BaseCommand):
    help = 'Наполнение базы данных первичными данными МУ им. С.Ю. Витте'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('=== Начало сидирования данных МУ им. С.Ю. Витте ==='))

        # 1. Факультеты
        faculties_data = [
            {
                'name': 'Факультет информационных технологий',
                'code': 'ФИТ',
                'description': 'Подготовка специалистов в сфере IT, программной инженерии, информационной безопасности и аналитики данных.'
            },
            {
                'name': 'Факультет экономики и финансов',
                'code': 'ФЭФ',
                'description': 'Ведущий центр подготовки экономистов, финансистов, бухгалтеров и специалистов по налогообложению.'
            },
            {
                'name': 'Юридический факультет',
                'code': 'ЮФ',
                'description': 'Классическое юридическое образование с углубленным изучением гражданского, уголовного и корпоративного права.'
            },
            {
                'name': 'Факультет управления',
                'code': 'ФУ',
                'description': 'Подготовка управленцев для бизнеса, государственных структур и медиа-индустрии.'
            },
            {
                'name': 'Колледж МУ им. С.Ю. Витте',
                'code': 'СПОР',
                'description': 'Программы среднего профессионального образования для выпускников 9 и 11 классов.'
            }
        ]

        faculty_instances = {}
        for item in faculties_data:
            faculty, created = Faculty.objects.get_or_create(
                name=item['name'],
                defaults={'code': item['code'], 'description': item['description']}
            )
            faculty_instances[item['code']] = faculty
            action = 'Создан' if created else 'Существует'
            self.stdout.write(f'Факультет: [{faculty.code}] {faculty.name} ({action})')

        # 2. Предметы ЕГЭ / вступительных
        subjects_data = [
            {'name': 'Русский язык', 'min_score': 40, 'description': 'Обязательный предмет для всех направлений.'},
            {'name': 'Математика (профильная)', 'min_score': 39, 'description': 'Профильная математика для технических и экономических направлений.'},
            {'name': 'Обществознание', 'min_score': 42, 'description': 'Профильный предмет для юридических и управленческих направлений.'},
            {'name': 'Информатика и ИКТ', 'min_score': 44, 'description': 'Профильный предмет для факультета информационных технологий.'},
            {'name': 'История', 'min_score': 35, 'description': 'Вступительный предмет для гуманитарных и юридических специальностей.'},
            {'name': 'Иностранный язык (английский)', 'min_score': 30, 'description': 'Вступительный предмет по выбору.'},
            {'name': 'Физика', 'min_score': 39, 'description': 'Вступительный предмет по выбору для IT и инженерии.'},
            {'name': 'Биология', 'min_score': 39, 'description': 'Вступительный предмет по выбору.'}
        ]

        for s_item in subjects_data:
            subj, created = ExamSubject.objects.get_or_create(
                name=s_item['name'],
                defaults={'min_score': s_item['min_score'], 'description': s_item['description']}
            )
            action = 'Создан' if created else 'Существует'
            self.stdout.write(f'Предмет ЕГЭ: {subj.name} (мин. {subj.min_score}) ({action})')

        # 3. Направления подготовки Витте
        fit = faculty_instances['ФИТ']
        fef = faculty_instances['ФЭФ']
        uf = faculty_instances['ЮФ']
        fu = faculty_instances['ФУ']

        specialties_data = [
            {
                'faculty': fit,
                'code': '09.03.03',
                'name': 'Прикладная информатика',
                'education_level': Specialty.EducationLevel.BACHELOR,
                'budget_places': 30,
                'paid_places': 120,
            },
            {
                'faculty': fit,
                'code': '09.03.01',
                'name': 'Информатика и вычислительная техника',
                'education_level': Specialty.EducationLevel.BACHELOR,
                'budget_places': 25,
                'paid_places': 80,
            },
            {
                'faculty': fit,
                'code': '09.04.03',
                'name': 'Прикладная информатика',
                'education_level': Specialty.EducationLevel.MASTER,
                'budget_places': 10,
                'paid_places': 40,
            },
            {
                'faculty': fef,
                'code': '38.03.01',
                'name': 'Экономика',
                'education_level': Specialty.EducationLevel.BACHELOR,
                'budget_places': 20,
                'paid_places': 150,
            },
            {
                'faculty': fef,
                'code': '38.04.01',
                'name': 'Экономика',
                'education_level': Specialty.EducationLevel.MASTER,
                'budget_places': 5,
                'paid_places': 60,
            },
            {
                'faculty': uf,
                'code': '40.03.01',
                'name': 'Юриспруденция',
                'education_level': Specialty.EducationLevel.BACHELOR,
                'budget_places': 20,
                'paid_places': 200,
            },
            {
                'faculty': uf,
                'code': '40.04.01',
                'name': 'Юриспруденция',
                'education_level': Specialty.EducationLevel.MASTER,
                'budget_places': 5,
                'paid_places': 80,
            },
            {
                'faculty': fu,
                'code': '38.03.02',
                'name': 'Менеджмент',
                'education_level': Specialty.EducationLevel.BACHELOR,
                'budget_places': 15,
                'paid_places': 130,
            },
            {
                'faculty': fu,
                'code': '38.03.04',
                'name': 'Государственное и муниципальное управление',
                'education_level': Specialty.EducationLevel.BACHELOR,
                'budget_places': 10,
                'paid_places': 90,
            },
            {
                'faculty': fu,
                'code': '42.03.01',
                'name': 'Реклама и связи с общественностью',
                'education_level': Specialty.EducationLevel.BACHELOR,
                'budget_places': 10,
                'paid_places': 100,
            },
        ]

        specialty_instances = {}
        for sp_item in specialties_data:
            spec, created = Specialty.objects.get_or_create(
                code=sp_item['code'],
                name=sp_item['name'],
                education_level=sp_item['education_level'],
                defaults={
                    'faculty': sp_item['faculty'],
                    'budget_places': sp_item['budget_places'],
                    'paid_places': sp_item['paid_places'],
                    'is_active': True,
                }
            )
            specialty_instances[f"{spec.code}_{spec.education_level}"] = spec
            action = 'Создано' if created else 'Существует'
            self.stdout.write(f'Направление: {spec.code} {spec.name} ({spec.get_education_level_display()}) ({action})')

        # 4. Программы обучения (EducationProgram)
        programs_data = [
            # 09.03.03 Прикладная информатика
            {
                'specialty': specialty_instances.get('09.03.03_BACHELOR'),
                'study_form': EducationProgram.StudyForm.FULL_TIME,
                'tuition_fee': Decimal('220000.00'),
                'duration': '4 года',
            },
            {
                'specialty': specialty_instances.get('09.03.03_BACHELOR'),
                'study_form': EducationProgram.StudyForm.PART_TIME,
                'tuition_fee': Decimal('115000.00'),
                'duration': '4 года 6 месяцев',
            },
            {
                'specialty': specialty_instances.get('09.03.03_BACHELOR'),
                'study_form': EducationProgram.StudyForm.MIXED,
                'tuition_fee': Decimal('145000.00'),
                'duration': '4 года 6 месяцев',
            },
            # 38.03.01 Экономика
            {
                'specialty': specialty_instances.get('38.03.01_BACHELOR'),
                'study_form': EducationProgram.StudyForm.FULL_TIME,
                'tuition_fee': Decimal('210000.00'),
                'duration': '4 года',
            },
            {
                'specialty': specialty_instances.get('38.03.01_BACHELOR'),
                'study_form': EducationProgram.StudyForm.PART_TIME,
                'tuition_fee': Decimal('110000.00'),
                'duration': '4 года 6 месяцев',
            },
            # 40.03.01 Юриспруденция
            {
                'specialty': specialty_instances.get('40.03.01_BACHELOR'),
                'study_form': EducationProgram.StudyForm.FULL_TIME,
                'tuition_fee': Decimal('230000.00'),
                'duration': '4 года',
            },
            {
                'specialty': specialty_instances.get('40.03.01_BACHELOR'),
                'study_form': EducationProgram.StudyForm.MIXED,
                'tuition_fee': Decimal('155000.00'),
                'duration': '4 года 6 месяцев',
            },
            # 38.03.02 Менеджмент
            {
                'specialty': specialty_instances.get('38.03.02_BACHELOR'),
                'study_form': EducationProgram.StudyForm.FULL_TIME,
                'tuition_fee': Decimal('210000.00'),
                'duration': '4 года',
            },
            {
                'specialty': specialty_instances.get('38.03.02_BACHELOR'),
                'study_form': EducationProgram.StudyForm.PART_TIME,
                'tuition_fee': Decimal('110000.00'),
                'duration': '4 года 6 месяцев',
            },
        ]

        for p_item in programs_data:
            if not p_item['specialty']:
                continue
            prog, created = EducationProgram.objects.get_or_create(
                specialty=p_item['specialty'],
                study_form=p_item['study_form'],
                defaults={
                    'tuition_fee': p_item['tuition_fee'],
                    'duration': p_item['duration'],
                    'is_active': True,
                }
            )
            action = 'Создана' if created else 'Существует'
            self.stdout.write(f'Программа: {prog.specialty.code} ({prog.get_study_form_display()}) — {prog.tuition_fee} руб/год ({action})')

        # 5. Тестовые пользователи (администратор, сотрудник, абитуриент)
        # Администратор
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@witte.ru',
                'first_name': 'Администратор',
                'last_name': 'Системы',
                'role': User.Role.ADMIN,
                'is_staff': True,
                'is_superuser': True,
                'phone': '+7 (495) 500-03-03',
            }
        )
        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write(self.style.SUCCESS('Пользователь admin создан (пароль: admin123)'))

        # Сотрудник комиссии
        officer_user, created = User.objects.get_or_create(
            username='officer1',
            defaults={
                'email': 'officer@witte.ru',
                'first_name': 'Елена',
                'last_name': 'Смирнова',
                'role': User.Role.OFFICER,
                'is_staff': True,
                'phone': '+7 (495) 500-03-04',
            }
        )
        if created:
            officer_user.set_password('officer123')
            officer_user.save()
            OfficerProfile.objects.get_or_create(
                user=officer_user,
                defaults={'position': 'Ведущий специалист приемной комиссии', 'cabinet': 'А-204'}
            )
            self.stdout.write(self.style.SUCCESS('Пользователь officer1 создан (пароль: officer123)'))

        # Абитуриент
        applicant_user, created = User.objects.get_or_create(
            username='applicant1',
            defaults={
                'email': 'applicant@mail.ru',
                'first_name': 'Иван',
                'last_name': 'Иванов',
                'role': User.Role.APPLICANT,
                'phone': '+7 (916) 123-45-67',
            }
        )
        if created:
            applicant_user.set_password('applicant123')
            applicant_user.save()
            ApplicantProfile.objects.get_or_create(
                user=applicant_user,
                defaults={
                    'snils': '123-456-789 00',
                    'passport_series': '4515',
                    'passport_number': '123456',
                    'passport_issued_by': 'ГУ МВД России по г. Москве',
                    'address': 'г. Москва, ул. Автозаводская, д. 10',
                }
            )
            self.stdout.write(self.style.SUCCESS('Пользователь applicant1 создан (пароль: applicant123)'))

        self.stdout.write(self.style.SUCCESS('\n[УСПЕХ] База данных успешно наполнена тестовыми данными МУ им. С.Ю. Витте!'))
