import os
import random
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from admissions.models import (
    Faculty, Specialty, EducationProgram, ExamSubject,
    Application, ApplicationDocument, ExamScore
)
from accounts.models import ApplicantProfile, OfficerProfile
from audit.models import StatusLog, Notification
from feedback.models import FeedbackMessage

User = get_user_model()

# Valid minimal 1-page PDF file content
SAMPLE_PDF_BYTES = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Count 1/Kids[3 0 R]>>endobj\n"
    b"3 0 obj<</Type/Page/MediaBox[0 0 595 842]/Parent 2 0 R/Resources<<>>>>endobj\n"
    b"xref\n"
    b"0 4\n"
    b"0000000000 65535 f \n"
    b"0000000009 00000 n \n"
    b"0000000052 00000 n \n"
    b"0000000102 00000 n \n"
    b"trailer<</Size 4/Root 1 0 R>>\n"
    b"startxref\n"
    b"178\n"
    b"%%EOF\n"
)


class Command(BaseCommand):
    help = 'Наполнение базы данных реалистичными демонстрационными данными МУ им. С.Ю. Витте с 14-дневной динамикой'

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE('=== Начало сидирования реалистичных данных МУ им. С.Ю. Витте ==='))

        now = timezone.now()

        # ---------------------------------------------------------------------
        # 1. Факультеты и институты
        # ---------------------------------------------------------------------
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

        # ---------------------------------------------------------------------
        # 2. Предметы ЕГЭ / вступительных
        # ---------------------------------------------------------------------
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

        subject_instances = {}
        for s_item in subjects_data:
            subj, created = ExamSubject.objects.get_or_create(
                name=s_item['name'],
                defaults={'min_score': s_item['min_score'], 'description': s_item['description']}
            )
            subject_instances[subj.name] = subj

        # ---------------------------------------------------------------------
        # 3. Направления подготовки Витте (включая Колледж СПОР)
        # ---------------------------------------------------------------------
        fit = faculty_instances['ФИТ']
        fef = faculty_instances['ФЭФ']
        uf = faculty_instances['ЮФ']
        fu = faculty_instances['ФУ']
        spor = faculty_instances['СПОР']

        specialties_data = [
            # ФИТ
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
            # ФЭФ
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
            # ЮФ
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
            # ФУ
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
            # Колледж (СПОР)
            {
                'faculty': spor,
                'code': '09.02.07',
                'name': 'Информационные системы и программирование',
                'education_level': Specialty.EducationLevel.COLLEGE,
                'budget_places': 15,
                'paid_places': 90,
            },
            {
                'faculty': spor,
                'code': '38.02.01',
                'name': 'Экономика и бухгалтерский учет (по отраслям)',
                'education_level': Specialty.EducationLevel.COLLEGE,
                'budget_places': 10,
                'paid_places': 80,
            },
            {
                'faculty': spor,
                'code': '40.02.01',
                'name': 'Право и организация социального обеспечения',
                'education_level': Specialty.EducationLevel.COLLEGE,
                'budget_places': 10,
                'paid_places': 70,
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

        # ---------------------------------------------------------------------
        # 4. Образовательные программы (EducationProgram)
        # ---------------------------------------------------------------------
        programs_data = [
            # 09.03.03 Прикладная информатика
            {'key': '09.03.03_BACHELOR', 'form': EducationProgram.StudyForm.FULL_TIME, 'fee': Decimal('220000.00'), 'dur': '4 года'},
            {'key': '09.03.03_BACHELOR', 'form': EducationProgram.StudyForm.PART_TIME, 'fee': Decimal('115000.00'), 'dur': '4 года 6 месяцев'},
            {'key': '09.03.03_BACHELOR', 'form': EducationProgram.StudyForm.MIXED, 'fee': Decimal('145000.00'), 'dur': '4 года 6 месяцев'},
            # 09.03.01 Информатика и вычислительная техника
            {'key': '09.03.01_BACHELOR', 'form': EducationProgram.StudyForm.FULL_TIME, 'fee': Decimal('225000.00'), 'dur': '4 года'},
            {'key': '09.03.01_BACHELOR', 'form': EducationProgram.StudyForm.PART_TIME, 'fee': Decimal('115000.00'), 'dur': '4 года 6 месяцев'},
            # 09.04.03 Прикладная информатика (Магистратура)
            {'key': '09.04.03_MASTER', 'form': EducationProgram.StudyForm.FULL_TIME, 'fee': Decimal('235000.00'), 'dur': '2 года'},
            {'key': '09.04.03_MASTER', 'form': EducationProgram.StudyForm.MIXED, 'fee': Decimal('150000.00'), 'dur': '2 года 6 месяцев'},
            # 38.03.01 Экономика
            {'key': '38.03.01_BACHELOR', 'form': EducationProgram.StudyForm.FULL_TIME, 'fee': Decimal('210000.00'), 'dur': '4 года'},
            {'key': '38.03.01_BACHELOR', 'form': EducationProgram.StudyForm.PART_TIME, 'fee': Decimal('110000.00'), 'dur': '4 года 6 месяцев'},
            # 38.04.01 Экономика (Магистратура)
            {'key': '38.04.01_MASTER', 'form': EducationProgram.StudyForm.FULL_TIME, 'fee': Decimal('225000.00'), 'dur': '2 года'},
            {'key': '38.04.01_MASTER', 'form': EducationProgram.StudyForm.MIXED, 'fee': Decimal('140000.00'), 'dur': '2 года 6 месяцев'},
            # 40.03.01 Юриспруденция
            {'key': '40.03.01_BACHELOR', 'form': EducationProgram.StudyForm.FULL_TIME, 'fee': Decimal('230000.00'), 'dur': '4 года'},
            {'key': '40.03.01_BACHELOR', 'form': EducationProgram.StudyForm.MIXED, 'fee': Decimal('155000.00'), 'dur': '4 года 6 месяцев'},
            # 40.04.01 Юриспруденция (Магистратура)
            {'key': '40.04.01_MASTER', 'form': EducationProgram.StudyForm.FULL_TIME, 'fee': Decimal('240000.00'), 'dur': '2 года'},
            {'key': '40.04.01_MASTER', 'form': EducationProgram.StudyForm.MIXED, 'fee': Decimal('155000.00'), 'dur': '2 года 6 месяцев'},
            # 38.03.02 Менеджмент
            {'key': '38.03.02_BACHELOR', 'form': EducationProgram.StudyForm.FULL_TIME, 'fee': Decimal('210000.00'), 'dur': '4 года'},
            {'key': '38.03.02_BACHELOR', 'form': EducationProgram.StudyForm.PART_TIME, 'fee': Decimal('110000.00'), 'dur': '4 года 6 месяцев'},
            # 38.03.04 ГМУ
            {'key': '38.03.04_BACHELOR', 'form': EducationProgram.StudyForm.FULL_TIME, 'fee': Decimal('210000.00'), 'dur': '4 года'},
            {'key': '38.03.04_BACHELOR', 'form': EducationProgram.StudyForm.PART_TIME, 'fee': Decimal('110000.00'), 'dur': '4 года 6 месяцев'},
            # 42.03.01 Реклама
            {'key': '42.03.01_BACHELOR', 'form': EducationProgram.StudyForm.FULL_TIME, 'fee': Decimal('215000.00'), 'dur': '4 года'},
            {'key': '42.03.01_BACHELOR', 'form': EducationProgram.StudyForm.PART_TIME, 'fee': Decimal('115000.00'), 'dur': '4 года 6 месяцев'},
            # Колледж: 09.02.07
            {'key': '09.02.07_COLLEGE', 'form': EducationProgram.StudyForm.FULL_TIME, 'fee': Decimal('130000.00'), 'dur': '3 года 10 месяцев'},
            # Колледж: 38.02.01
            {'key': '38.02.01_COLLEGE', 'form': EducationProgram.StudyForm.FULL_TIME, 'fee': Decimal('120000.00'), 'dur': '2 года 10 месяцев'},
            {'key': '38.02.01_COLLEGE', 'form': EducationProgram.StudyForm.PART_TIME, 'fee': Decimal('75000.00'), 'dur': '3 года 6 месяцев'},
            # Колледж: 40.02.01
            {'key': '40.02.01_COLLEGE', 'form': EducationProgram.StudyForm.FULL_TIME, 'fee': Decimal('125000.00'), 'dur': '2 года 10 месяцев'},
            {'key': '40.02.01_COLLEGE', 'form': EducationProgram.StudyForm.MIXED, 'fee': Decimal('85000.00'), 'dur': '3 года 6 месяцев'},
        ]

        program_lookup = {}
        for p_item in programs_data:
            spec = specialty_instances.get(p_item['key'])
            if not spec:
                continue
            prog, _ = EducationProgram.objects.get_or_create(
                specialty=spec,
                study_form=p_item['form'],
                defaults={
                    'tuition_fee': p_item['fee'],
                    'duration': p_item['dur'],
                    'is_active': True,
                }
            )
            program_lookup[(spec.code, spec.education_level, p_item['form'])] = prog

        # ---------------------------------------------------------------------
        # 5. Служебные пользователи (Администратор, Сотрудники комиссии)
        # ---------------------------------------------------------------------
        admin_user, _ = User.objects.get_or_create(
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
        admin_user.set_password('admin123')
        admin_user.role = User.Role.ADMIN
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.save()

        officer1, _ = User.objects.get_or_create(
            username='officer1',
            defaults={
                'email': 'smirnova@witte.ru',
                'first_name': 'Елена',
                'last_name': 'Смирнова',
                'role': User.Role.OFFICER,
                'is_staff': True,
                'phone': '+7 (495) 500-03-04',
            }
        )
        officer1.set_password('officer123')
        officer1.role = User.Role.OFFICER
        officer1.is_staff = True
        officer1.save()
        OfficerProfile.objects.get_or_create(
            user=officer1,
            defaults={'position': 'Ведущий специалист приемной комиссии', 'cabinet': 'А-204'}
        )

        officer2, _ = User.objects.get_or_create(
            username='officer2',
            defaults={
                'email': 'kuznetsov@witte.ru',
                'first_name': 'Михаил',
                'last_name': 'Кузнецов',
                'role': User.Role.OFFICER,
                'is_staff': True,
                'phone': '+7 (495) 500-03-05',
            }
        )
        officer2.set_password('officer123')
        officer2.role = User.Role.OFFICER
        officer2.is_staff = True
        officer2.save()
        OfficerProfile.objects.get_or_create(
            user=officer2,
            defaults={'position': 'Специалист по проверке документов', 'cabinet': 'А-205'}
        )

        # ---------------------------------------------------------------------
        # 6. Очистка старых тестовых заявлений для чистого наполнения
        # ---------------------------------------------------------------------
        self.stdout.write('Сброс предыдущих тестовых заявлений...')
        # Delete old applications (cascades to docs, scores, logs)
        Application.objects.all().delete()
        Notification.objects.all().delete()

        # ---------------------------------------------------------------------
        # 7. Список 42 реалистичных абитуриентов и заявлений
        # ---------------------------------------------------------------------
        applicants_def = [
            ('Иванов', 'Иван', 'Сергеевич', 'applicant1', 'applicant@mail.ru', '4515', '123456', 'г. Москва, ул. Автозаводская, д. 10'),
            ('Смирнов', 'Артём', 'Владимирович', 'smirnov_a', 'smirnov_artem@yandex.ru', '4516', '234567', 'г. Москва, Варшавское шоссе, д. 45'),
            ('Кузнецова', 'София', 'Александровна', 'kuznetsova_s', 'sofia.kuzn@gmail.com', '4517', '345678', 'г. Подольск, ул. Кирова, д. 12'),
            ('Попов', 'Александр', 'Дмитриевич', 'popov_alex', 'popov.alex9@mail.ru', '4518', '456789', 'г. Москва, ул. Профсоюзная, д. 88'),
            ('Васильева', 'Анна', 'Игоревна', 'vasilieva_a', 'anya_vasilieva@bk.ru', '4519', '567890', 'г. Люберцы, Октябрьский пр-т, д. 15'),
            ('Петров', 'Максим', 'Олегович', 'petrov_max', 'max_petrov2008@inbox.ru', '4520', '678901', 'г. Москва, Ленинский пр-т, д. 104'),
            ('Соколова', 'Мария', 'Андреевна', 'sokolova_m', 'masha.sok@yandex.ru', '4521', '789012', 'г. Химки, ул. Маяковского, д. 6'),
            ('Михайлов', 'Даниил', 'Романович', 'mikhailov_d', 'danya_mikh@mail.ru', '4522', '890123', 'г. Москва, ул. Первомайская, д. 32'),
            ('Новикова', 'Виктория', 'Денисовна', 'novikova_v', 'vika_novikova@gmail.com', '4523', '901234', 'г. Мытищи, Новомытищинский пр-т, д. 24'),
            ('Федоров', 'Дмитрий', 'Павлович', 'fedorov_d', 'fedorov_dima@list.ru', '4524', '112233', 'г. Москва, Каширское шоссе, д. 55'),
            ('Морозова', 'Дарья', 'Викторовна', 'morozova_d', 'dasha_morozova@mail.ru', '4525', '223344', 'г. Одинцово, ул. Можайское ш., д. 71'),
            ('Волков', 'Никита', 'Алексеевич', 'volkov_n', 'nikita_volkov@yandex.ru', '4526', '334455', 'г. Москва, ул. Люблинская, д. 112'),
            ('Алексеева', 'Елизавета', 'Константиновна', 'alekseeva_e', 'liza_alekseeva@gmail.com', '4527', '445566', 'г. Королев, ул. Циолковского, д. 18'),
            ('Лебедев', 'Иван', 'Григорьевич', 'lebedev_i', 'ivan.lebedev08@mail.ru', '4528', '556677', 'г. Москва, ул. Енисейская, д. 14'),
            ('Семенова', 'Анастасия', 'Юрьевна', 'semenova_a', 'nastya_semenova@bk.ru', '4529', '667788', 'г. Красногорск, ул. Ленина, д. 30'),
            ('Павлов', 'Егор', 'Валентинович', 'pavlov_e', 'egor_pavlov26@yandex.ru', '4530', '778899', 'г. Москва, Рязанский пр-т, д. 40'),
            ('Козлова', 'Полина', 'Сергеевна', 'kozlova_p', 'polina_kozlova@inbox.ru', '4531', '889900', 'г. Балашиха, ш. Энтузиастов, д. 52'),
            ('Степанов', 'Матвей', 'Николаевич', 'stepanov_m', 'matvey_step@mail.ru', '4532', '990011', 'г. Москва, ул. Тверская, д. 22'),
            ('Николаева', 'Екатерина', 'Витальевна', 'nikolaeva_e', 'kate_nikolaeva@gmail.com', '4533', '102030', 'г. Реутов, ул. Южная, д. 9'),
            ('Орлов', 'Кирилл', 'Артемович', 'orlov_k', 'kirill_orlov@list.ru', '4534', '203040', 'г. Москва, Дмитровское шоссе, д. 98'),
            ('Андреева', 'Ксения', 'Тимофеевна', 'andreeva_k', 'ksenia_andr@yandex.ru', '4535', '304050', 'г. Долгопрудный, Лихачевский пр-д, д. 4'),
            ('Макаров', 'Ярослав', 'Евгеньевич', 'makarov_y', 'yarik_makarov@mail.ru', '4536', '405060', 'г. Москва, ул. Чертановская, д. 44'),
            ('Захарова', 'Алина', 'Владиславовна', 'zakharova_a', 'alina_zakh@gmail.com', '4537', '506070', 'г. Видное, пр-т Ленинского Комсомола, д. 16'),
            ('Зайцев', 'Роман', 'Борисович', 'zaytsev_r', 'roman_zaytsev@bk.ru', '4538', '607080', 'г. Москва, ул. Братиславская, д. 26'),
            ('Соловьева', 'Валерия', 'Антоновна', 'solovieva_v', 'valeria_solov@yandex.ru', '4539', '708090', 'г. Зеленоград, корп. 1502'),
            ('Борисов', 'Тимофей', 'Ильич', 'borisov_t', 'timofey_bor@mail.ru', '4540', '809001', 'г. Москва, Волгоградский пр-т, д. 68'),
            ('Яковлева', 'Вероника', 'Станиславовна', 'yakovleva_v', 'veronika_yak@inbox.ru', '4541', '900112', 'г. Серпухов, ул. Советская, д. 35'),
            ('Беляев', 'Владислав', 'Михайлович', 'belyaev_v', 'vlad_belyaev@list.ru', '4542', '011223', 'г. Москва, ул. Менжинского, д. 19'),
            ('Григорьева', 'Милана', 'Данииловна', 'grigorieva_m', 'milana_grig@yandex.ru', '4543', '122334', 'г. Щёлково, Пролетарский пр-т, д. 8'),
            ('Романов', 'Марк', 'Семенович', 'romanov_m', 'mark_romanov@gmail.com', '4544', '233445', 'г. Москва, Мичуринский пр-т, д. 34'),
            ('Воробьева', 'Таисия', 'Олеговна', 'vorobieva_t', 'tasya_vorob@mail.ru', '4545', '344556', 'г. Раменское, ул. Гурьева, д. 11'),
            ('Сергеев', 'Арсений', 'Васильевич', 'sergeev_a', 'arseniy_serg@bk.ru', '4546', '455667', 'г. Москва, ул. Сходненская, д. 25'),
            ('Кузьмина', 'Кристина', 'Андреевна', 'kuzmina_k', 'kristina_kuzm@yandex.ru', '4547', '566778', 'г. Коломна, ул. Октябрьской революции, д. 210'),
            ('Фролов', 'Лев', 'Станиславович', 'frolov_l', 'lev_frolov@inbox.ru', '4548', '677889', 'г. Москва, Ломоносовский пр-т, д. 14'),
            ('Александрова', 'Диана', 'Игоревна', 'aleksandrova_d', 'diana_aleks@gmail.com', '4549', '788990', 'г. Электросталь, ул. Мира, д. 17'),
            ('Дмитриев', 'Глеб', 'Васильевич', 'dmitriev_g', 'gleb_dmitriev@list.ru', '4550', '899001', 'г. Москва, ул. Бутырская, д. 62'),
            ('Королева', 'Ульяна', 'Ярославовна', 'koroleva_u', 'ulyana_koroleva@mail.ru', '4551', '900113', 'г. Ногинск, ул. 3-го Интернационала, д. 42'),
            ('Гусев', 'Денис', 'Кириллович', 'gusev_d', 'denis_gusev26@yandex.ru', '4552', '011224', 'г. Москва, ул. Новослободская, д. 38'),
            ('Киселева', 'Василиса', 'Матвеевна', 'kiseleva_v', 'vasilisa_kis@bk.ru', '4553', '122335', 'г. Пушкино, Московский пр-т, д. 20'),
            ('Ильин', 'Федор', 'Георгиевич', 'ilyin_f', 'fedor_ilyin@gmail.com', '4554', '233446', 'г. Москва, ул. Таганская, д. 15'),
            ('Максимова', 'Мирослава', 'Львовна', 'maksimova_m', 'miroslava_max@inbox.ru', '4555', '344557', 'г. Чехов, ул. Чехова, д. 49'),
            ('Поляков', 'Богдан', 'Аркадьевич', 'polyakov_b', 'bogdan_polyakov@mail.ru', '4556', '455668', 'г. Москва, Измайловский б-р, д. 50'),
        ]

        created_users = []
        for i, item in enumerate(applicants_def):
            last_name, first_name, patronymic, username, email, p_ser, p_num, address = item
            u, _ = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': email,
                    'first_name': first_name,
                    'last_name': last_name,
                    'role': User.Role.APPLICANT,
                    'phone': f'+7 (9{10 + (i % 89):02d}) {100 + i:03d}-{(i * 7) % 90 + 10:02d}-{(i * 13) % 90 + 10:02d}',
                }
            )
            u.first_name = first_name
            u.last_name = last_name
            u.email = email
            u.role = User.Role.APPLICANT
            u.set_password('applicant123')
            u.save()

            snils_num = f"{112 + i:03d}-{245 + (i * 3) % 700:03d}-{389 + (i * 5) % 600:03d} {(i * 11) % 90 + 10:02d}"
            ApplicantProfile.objects.update_or_create(
                user=u,
                defaults={
                    'snils': snils_num,
                    'passport_series': p_ser,
                    'passport_number': p_num,
                    'passport_issued_by': 'ГУ МВД России по г. Москве и Московской области',
                    'address': address,
                }
            )
            created_users.append(u)

        self.stdout.write(self.style.SUCCESS(f'Создано абитуриентов: {len(created_users)}'))

        # ---------------------------------------------------------------------
        # 8. Спецификация 42 заявлений (с датами за последние 14 дней)
        # ---------------------------------------------------------------------
        applications_plan = [
            # Day 13 ago (1 app)
            {
                'u': 0, 'code': '09.03.03', 'lvl': Specialty.EducationLevel.BACHELOR, 'form': EducationProgram.StudyForm.FULL_TIME,
                'fin': Application.FinancingType.BUDGET, 'status': Application.Status.ENROLLED,
                'days_ago': 13, 'enrolled_days_ago': 10, 'order_num': '26-08/БЮД-1',
                'scores': {'Русский язык': 88, 'Математика (профильная)': 84, 'Информатика и ИКТ': 92},
                'docs': True, 'comment': 'Зачислен на бюджетные места 1 волны приказом № 26-08/БЮД-1.'
            },
            # Day 12 ago (2 apps)
            {
                'u': 1, 'code': '38.03.01', 'lvl': Specialty.EducationLevel.BACHELOR, 'form': EducationProgram.StudyForm.FULL_TIME,
                'fin': Application.FinancingType.BUDGET, 'status': Application.Status.ENROLLED,
                'days_ago': 12, 'enrolled_days_ago': 8, 'order_num': '26-08/БЮД-2',
                'scores': {'Русский язык': 85, 'Математика (профильная)': 82, 'Обществознание': 88},
                'docs': True, 'comment': 'Зачислен на бюджетные места 1 волны приказом № 26-08/БЮД-2.'
            },
            {
                'u': 2, 'code': '40.03.01', 'lvl': Specialty.EducationLevel.BACHELOR, 'form': EducationProgram.StudyForm.FULL_TIME,
                'fin': Application.FinancingType.PAID, 'status': Application.Status.ENROLLED,
                'days_ago': 12, 'enrolled_days_ago': 7, 'order_num': '26-08/ПЛАТ-1',
                'scores': {'Русский язык': 78, 'Обществознание': 82, 'История': 76},
                'docs': True, 'comment': 'Договор на оказание платных образовательных услуг заключен, зачислен.'
            },
            # Day 11 ago (2 apps)
            {
                'u': 3, 'code': '09.03.01', 'lvl': Specialty.EducationLevel.BACHELOR, 'form': EducationProgram.StudyForm.FULL_TIME,
                'fin': Application.FinancingType.BUDGET, 'status': Application.Status.APPROVED,
                'days_ago': 11, 'enrolled_days_ago': None, 'order_num': None,
                'scores': {'Русский язык': 82, 'Математика (профильная)': 85, 'Информатика и ИКТ': 80},
                'docs': True, 'comment': 'Оригинал аттестата предоставлен. Допущен к участию в бюджетном конкурсе.'
            },
            {
                'u': 4, 'code': '09.02.07', 'lvl': Specialty.EducationLevel.COLLEGE, 'form': EducationProgram.StudyForm.FULL_TIME,
                'fin': Application.FinancingType.BUDGET, 'status': Application.Status.ENROLLED,
                'days_ago': 11, 'enrolled_days_ago': 5, 'order_num': '26-08/СПО-1',
                'scores': {'Русский язык': 78, 'Математика (профильная)': 82},
                'docs': True, 'comment': 'Зачислен в колледж на бюджетные места.'
            },
            # Day 10 ago (3 apps)
            {
                'u': 5, 'code': '38.03.01', 'lvl': Specialty.EducationLevel.BACHELOR, 'form': EducationProgram.StudyForm.PART_TIME,
                'fin': Application.FinancingType.PAID, 'status': Application.Status.APPROVED,
                'days_ago': 10, 'enrolled_days_ago': None, 'order_num': None,
                'scores': {'Русский язык': 68, 'Математика (профильная)': 65, 'Обществознание': 70},
                'docs': True, 'comment': 'Документы проверены, сформирован договор на заочную форму.'
            },
            {
                'u': 6, 'code': '09.03.03', 'lvl': Specialty.EducationLevel.BACHELOR, 'form': EducationProgram.StudyForm.MIXED,
                'fin': Application.FinancingType.PAID, 'status': Application.Status.ENROLLED,
                'days_ago': 10, 'enrolled_days_ago': 5, 'order_num': '26-08/ПЛАТ-2',
                'scores': {'Русский язык': 74, 'Математика (профильная)': 72, 'Информатика и ИКТ': 76},
                'docs': True, 'comment': 'Оплата 1 семестра подтверждена бухгалтерией. Зачислен.'
            },
            {
                'u': 7, 'code': '40.03.01', 'lvl': Specialty.EducationLevel.BACHELOR, 'form': EducationProgram.StudyForm.MIXED,
                'fin': Application.FinancingType.PAID, 'status': Application.Status.REJECTED,
                'days_ago': 10, 'enrolled_days_ago': None, 'order_num': None,
                'scores': {'Русский язык': 55, 'Обществознание': 36, 'История': 48},
                'docs': False, 'comment': 'Отклонено: балл ЕГЭ по обществознанию (36) ниже установленного порога (42).'
            },
            # Day 9 ago (2 apps)
            {
                'u': 8, 'code': '09.04.03', 'lvl': Specialty.EducationLevel.MASTER, 'form': EducationProgram.StudyForm.FULL_TIME,
                'fin': Application.FinancingType.BUDGET, 'status': Application.Status.ENROLLED,
                'days_ago': 9, 'enrolled_days_ago': 4, 'order_num': '26-08/МАГ-1',
                'scores': {'Русский язык': 92, 'Математика (профильная)': 88, 'Информатика и ИКТ': 94},
                'docs': True, 'comment': 'Диплом бакалавра с отличием. Зачислен на бюджет магистратуры.'
            },
            {
                'u': 9, 'code': '38.03.02', 'lvl': Specialty.EducationLevel.BACHELOR, 'form': EducationProgram.StudyForm.FULL_TIME,
                'fin': Application.FinancingType.BUDGET, 'status': Application.Status.APPROVED,
                'days_ago': 9, 'enrolled_days_ago': None, 'order_num': None,
                'scores': {'Русский язык': 82, 'Математика (профильная)': 78, 'Обществознание': 84},
                'docs': True, 'comment': 'Допущен к общему конкурсу на бюджет Менеджмента.'
            },
            # Day 8 ago (4 apps)
            {
                'u': 10, 'code': '09.03.01', 'lvl': Specialty.EducationLevel.BACHELOR, 'form': EducationProgram.StudyForm.FULL_TIME,
                'fin': Application.FinancingType.PAID, 'status': Application.Status.ENROLLED,
                'days_ago': 8, 'enrolled_days_ago': 3, 'order_num': '26-08/ПЛАТ-3',
                'scores': {'Русский язык': 72, 'Математика (профильная)': 70, 'Информатика и ИКТ': 75},
                'docs': True, 'comment': 'Договор подписан, оплата первого семестра внесена.'
            },
            {
                'u': 11, 'code': '38.04.01', 'lvl': Specialty.EducationLevel.MASTER, 'form': EducationProgram.StudyForm.FULL_TIME,
                'fin': Application.FinancingType.PAID, 'status': Application.Status.ENROLLED,
                'days_ago': 8, 'enrolled_days_ago': 3, 'order_num': '26-08/МАГ-2',
                'scores': {'Русский язык': 86, 'Математика (профильная)': 84, 'Обществознание': 88},
                'docs': True, 'comment': 'Зачислен в магистратуру на очную форму обучения.'
            },
            {
                'u': 12, 'code': '40.04.01', 'lvl': Specialty.EducationLevel.MASTER, 'form': EducationProgram.StudyForm.FULL_TIME,
                'fin': Application.FinancingType.BUDGET, 'status': Application.Status.APPROVED,
                'days_ago': 8, 'enrolled_days_ago': None, 'order_num': None,
                'scores': {'Русский язык': 90, 'Обществознание': 88, 'История': 85},
                'docs': True, 'comment': 'Высокий рейтинг в списке поступающих в магистратуру ЮФ.'
            },
            {
                'u': 13, 'code': '38.02.01', 'lvl': Specialty.EducationLevel.COLLEGE, 'form': EducationProgram.StudyForm.FULL_TIME,
                'fin': Application.FinancingType.PAID, 'status': Application.Status.APPROVED,
                'days_ago': 8, 'enrolled_days_ago': None, 'order_num': None,
                'scores': {'Русский язык': 70, 'Математика (профильная)': 68},
                'docs': True, 'comment': 'Пакет документов для колледжа проверен и принят.'
            },
            # Day 7 ago (3 apps)
            {
                'u': 14, 'code': '09.03.03', 'lvl': Specialty.EducationLevel.BACHELOR, 'form': EducationProgram.StudyForm.FULL_TIME,
                'fin': Application.FinancingType.BUDGET, 'status': Application.Status.ENROLLED,
                'days_ago': 7, 'enrolled_days_ago': 2, 'order_num': '26-08/БЮД-3',
                'scores': {'Русский язык': 88, 'Математика (профильная)': 90, 'Информатика и ИКТ': 92},
                'docs': True, 'comment': 'Зачислен приказом № 26-08/БЮД-3. Топ рейтинга.'
            },
            {
                'u': 15, 'code': '38.03.01', 'lvl': Specialty.EducationLevel.BACHELOR, 'form': EducationProgram.StudyForm.FULL_TIME,
                'fin': Application.FinancingType.PAID, 'status': Application.Status.APPROVED,
                'days_ago': 7, 'enrolled_days_ago': None, 'order_num': None,
                'scores': {'Русский язык': 74, 'Математика (профильная)': 72, 'Обществознание': 76},
                'docs': True, 'comment': 'Договор выслан на согласование абитуриенту.'
            },
            {
                'u': 16, 'code': '40.03.01', 'lvl': Specialty.EducationLevel.BACHELOR, 'form': EducationProgram.StudyForm.FULL_TIME,
                'fin': Application.FinancingType.BUDGET, 'status': Application.Status.ENROLLED,
                'days_ago': 7, 'enrolled_days_ago': 1, 'order_num': '26-08/БЮД-4',
                'scores': {'Русский язык': 92, 'Обществознание': 94, 'История': 88},
                'docs': True, 'comment': 'Зачислен приказом № 26-08/БЮД-4 на бюджет.'
            },
            # Day 6 ago (4 apps)
            {
                'u': 17, 'code': '09.03.01', 'lvl': Specialty.EducationLevel.BACHELOR, 'form': EducationProgram.StudyForm.PART_TIME,
                'fin': Application.FinancingType.PAID, 'status': Application.Status.APPROVED,
                'days_ago': 6, 'enrolled_days_ago': None, 'order_num': None,
                'scores': {'Русский язык': 66, 'Математика (профильная)': 64, 'Информатика и ИКТ': 70},
                'docs': True, 'comment': 'Заочное отделение. Допущен к конкурсу.'
            },
            {
                'u': 18, 'code': '38.03.01', 'lvl': Specialty.EducationLevel.BACHELOR, 'form': EducationProgram.StudyForm.PART_TIME,
                'fin': Application.FinancingType.PAID, 'status': Application.Status.APPROVED,
                'days_ago': 6, 'enrolled_days_ago': None, 'order_num': None,
                'scores': {'Русский язык': 65, 'Математика (профильная)': 62, 'Обществознание': 68},
                'docs': True, 'comment': 'Одобрено. Ожидание оплаты.'
            },
            {
                'u': 19, 'code': '40.03.01', 'lvl': Specialty.EducationLevel.BACHELOR, 'form': EducationProgram.StudyForm.MIXED,
                'fin': Application.FinancingType.PAID, 'status': Application.Status.WITHDRAWN,
                'days_ago': 6, 'enrolled_days_ago': None, 'order_num': None,
                'scores': {'Русский язык': 70, 'Обществознание': 72, 'История': 68},
                'docs': False, 'comment': 'Отозвано абитуриентом в связи с выбором другого направления.'
            },
            {
                'u': 20, 'code': '40.02.01', 'lvl': Specialty.EducationLevel.COLLEGE, 'form': EducationProgram.StudyForm.FULL_TIME,
                'fin': Application.FinancingType.BUDGET, 'status': Application.Status.APPROVED,
                'days_ago': 6, 'enrolled_days_ago': None, 'order_num': None,
                'scores': {'Русский язык': 76, 'Математика (профильная)': 72},
                'docs': True, 'comment': 'Колледж: оригинал аттестата 9 классов проверен.'
            },
            # Day 5 ago (5 apps)
            {
                'u': 21, 'code': '09.03.03', 'lvl': Specialty.EducationLevel.BACHELOR, 'form': EducationProgram.StudyForm.FULL_TIME,
                'fin': Application.FinancingType.BUDGET, 'status': Application.Status.APPROVED,
                'days_ago': 5, 'enrolled_days_ago': None, 'order_num': None,
                'scores': {'Русский язык': 82, 'Математика (профильная)': 84, 'Информатика и ИКТ': 86},
                'docs': True, 'comment': 'Допущен к конкурсу на бюджет ФИТ.'
            },
            {
                'u': 22, 'code': '09.03.01', 'lvl': Specialty.EducationLevel.BACHELOR, 'form': EducationProgram.StudyForm.FULL_TIME,
                'fin': Application.FinancingType.BUDGET, 'status': Application.Status.APPROVED,
                'days_ago': 5, 'enrolled_days_ago': None, 'order_num': None,
                'scores': {'Русский язык': 84, 'Математика (профильная)': 82, 'Информатика и ИКТ': 85},
                'docs': True, 'comment': 'Участие в конкурсе на бюджет ИВТ.'
            },
            {
                'u': 23, 'code': '38.03.01', 'lvl': Specialty.EducationLevel.BACHELOR, 'form': EducationProgram.StudyForm.FULL_TIME,
                'fin': Application.FinancingType.BUDGET, 'status': Application.Status.APPROVED,
                'days_ago': 5, 'enrolled_days_ago': None, 'order_num': None,
                'scores': {'Русский язык': 86, 'Математика (профильная)': 80, 'Обществознание': 84},
                'docs': True, 'comment': 'Проверен, входит в число претендентов на бюджет.'
            },
            {
                'u': 24, 'code': '40.03.01', 'lvl': Specialty.EducationLevel.BACHELOR, 'form': EducationProgram.StudyForm.FULL_TIME,
                'fin': Application.FinancingType.PAID, 'status': Application.Status.APPROVED,
                'days_ago': 5, 'enrolled_days_ago': None, 'order_num': None,
                'scores': {'Русский язык': 76, 'Обществознание': 80, 'История': 74},
                'docs': True, 'comment': 'Платная основа Юриспруденции одобрена.'
            },
            {
                'u': 25, 'code': '42.03.01', 'lvl': Specialty.EducationLevel.BACHELOR, 'form': EducationProgram.StudyForm.FULL_TIME,
                'fin': Application.FinancingType.PAID, 'status': Application.Status.REJECTED,
                'days_ago': 5, 'enrolled_days_ago': None, 'order_num': None,
                'scores': {'Русский язык': 60, 'Математика (профильная)': 32, 'Обществознание': 62},
                'docs': False, 'comment': 'Отклонено: математика ниже минимального балла (32 < 39).'
            },
            # Day 4 ago (3 apps)
            {
                'u': 26, 'code': '09.04.03', 'lvl': Specialty.EducationLevel.MASTER, 'form': EducationProgram.StudyForm.MIXED,
                'fin': Application.FinancingType.PAID, 'status': Application.Status.UNDER_REVIEW,
                'days_ago': 4, 'enrolled_days_ago': None, 'order_num': None,
                'scores': {'Русский язык': 75, 'Математика (профильная)': 74, 'Информатика и ИКТ': 80},
                'docs': 'partial', 'comment': 'Специалист проверяет диплом бакалавра.'
            },
            {
                'u': 27, 'code': '38.04.01', 'lvl': Specialty.EducationLevel.MASTER, 'form': EducationProgram.StudyForm.MIXED,
                'fin': Application.FinancingType.PAID, 'status': Application.Status.UNDER_REVIEW,
                'days_ago': 4, 'enrolled_days_ago': None, 'order_num': None,
                'scores': {'Русский язык': 72, 'Математика (профильная)': 70, 'Обществознание': 75},
                'docs': 'partial', 'comment': 'Проверка приложения к диплому.'
            },
            {
                'u': 28, 'code': '09.02.07', 'lvl': Specialty.EducationLevel.COLLEGE, 'form': EducationProgram.StudyForm.FULL_TIME,
                'fin': Application.FinancingType.PAID, 'status': Application.Status.DOCUMENTS_REQUIRED,
                'days_ago': 4, 'enrolled_days_ago': None, 'order_num': None,
                'scores': {'Русский язык': 66, 'Математика (профильная)': 70},
                'docs': 'partial', 'comment': 'Не читаем скан разворота паспорта с регистрацией.'
            },
            # Day 3 ago (4 apps)
            {
                'u': 29, 'code': '09.03.03', 'lvl': Specialty.EducationLevel.BACHELOR, 'form': EducationProgram.StudyForm.FULL_TIME,
                'fin': Application.FinancingType.PAID, 'status': Application.Status.UNDER_REVIEW,
                'days_ago': 3, 'enrolled_days_ago': None, 'order_num': None,
                'scores': {'Русский язык': 74, 'Математика (профильная)': 72, 'Информатика и ИКТ': 78},
                'docs': 'partial', 'comment': 'Заявление принято на рассмотрение.'
            },
            {
                'u': 30, 'code': '40.03.01', 'lvl': Specialty.EducationLevel.BACHELOR, 'form': EducationProgram.StudyForm.FULL_TIME,
                'fin': Application.FinancingType.BUDGET, 'status': Application.Status.UNDER_REVIEW,
                'days_ago': 3, 'enrolled_days_ago': None, 'order_num': None,
                'scores': {'Русский язык': 84, 'Обществознание': 86, 'История': 82},
                'docs': 'partial', 'comment': 'Проверка подлинности диплома олимпиады.'
            },
            {
                'u': 31, 'code': '38.03.01', 'lvl': Specialty.EducationLevel.BACHELOR, 'form': EducationProgram.StudyForm.PART_TIME,
                'fin': Application.FinancingType.PAID, 'status': Application.Status.DOCUMENTS_REQUIRED,
                'days_ago': 3, 'enrolled_days_ago': None, 'order_num': None,
                'scores': {'Русский язык': 62, 'Математика (профильная)': 58, 'Обществознание': 64},
                'docs': 'partial', 'comment': 'Требуется скан свидетельства о перемене фамилии.'
            },
            {
                'u': 32, 'code': '40.04.01', 'lvl': Specialty.EducationLevel.MASTER, 'form': EducationProgram.StudyForm.MIXED,
                'fin': Application.FinancingType.PAID, 'status': Application.Status.REJECTED,
                'days_ago': 3, 'enrolled_days_ago': None, 'order_num': None,
                'scores': {'Русский язык': 38, 'Обществознание': 74, 'История': 70},
                'docs': False, 'comment': 'Отклонено: русский язык ниже установленного порога (38 < 40).'
            },
            # Day 2 ago (4 apps)
            {
                'u': 33, 'code': '09.03.01', 'lvl': Specialty.EducationLevel.BACHELOR, 'form': EducationProgram.StudyForm.FULL_TIME,
                'fin': Application.FinancingType.BUDGET, 'status': Application.Status.UNDER_REVIEW,
                'days_ago': 2, 'enrolled_days_ago': None, 'order_num': None,
                'scores': {'Русский язык': 80, 'Математика (профильная)': 78, 'Информатика и ИКТ': 82},
                'docs': 'partial', 'comment': 'Проверка оригиналов в системе ФИС ГИА.'
            },
            {
                'u': 34, 'code': '38.03.01', 'lvl': Specialty.EducationLevel.BACHELOR, 'form': EducationProgram.StudyForm.FULL_TIME,
                'fin': Application.FinancingType.PAID, 'status': Application.Status.UNDER_REVIEW,
                'days_ago': 2, 'enrolled_days_ago': None, 'order_num': None,
                'scores': {'Русский язык': 70, 'Математика (профильная)': 68, 'Обществознание': 72},
                'docs': 'partial', 'comment': 'Специалист назначен на карточку заявления.'
            },
            {
                'u': 35, 'code': '40.03.01', 'lvl': Specialty.EducationLevel.BACHELOR, 'form': EducationProgram.StudyForm.MIXED,
                'fin': Application.FinancingType.PAID, 'status': Application.Status.DOCUMENTS_REQUIRED,
                'days_ago': 2, 'enrolled_days_ago': None, 'order_num': None,
                'scores': {'Русский язык': 72, 'Обществознание': 70, 'История': 66},
                'docs': 'partial', 'comment': 'Загружена неполная копия аттестата (нет приложения с оценками).'
            },
            {
                'u': 36, 'code': '38.02.01', 'lvl': Specialty.EducationLevel.COLLEGE, 'form': EducationProgram.StudyForm.PART_TIME,
                'fin': Application.FinancingType.PAID, 'status': Application.Status.SUBMITTED,
                'days_ago': 2, 'enrolled_days_ago': None, 'order_num': None,
                'scores': {'Русский язык': 64, 'Математика (профильная)': 62},
                'docs': 'partial', 'comment': 'Новое заявление, ожидает взятия в работу.'
            },
            # Day 1 ago (3 apps)
            {
                'u': 37, 'code': '09.03.03', 'lvl': Specialty.EducationLevel.BACHELOR, 'form': EducationProgram.StudyForm.FULL_TIME,
                'fin': Application.FinancingType.BUDGET, 'status': Application.Status.SUBMITTED,
                'days_ago': 1, 'enrolled_days_ago': None, 'order_num': None,
                'scores': {'Русский язык': 86, 'Математика (профильная)': 82, 'Информатика и ИКТ': 88},
                'docs': 'partial', 'comment': 'Подано через личный кабинет вчера.'
            },
            {
                'u': 38, 'code': '38.03.01', 'lvl': Specialty.EducationLevel.BACHELOR, 'form': EducationProgram.StudyForm.FULL_TIME,
                'fin': Application.FinancingType.BUDGET, 'status': Application.Status.SUBMITTED,
                'days_ago': 1, 'enrolled_days_ago': None, 'order_num': None,
                'scores': {'Русский язык': 82, 'Математика (профильная)': 84, 'Обществознание': 80},
                'docs': 'partial', 'comment': 'В очереди на первичную проверку оператором.'
            },
            {
                'u': 39, 'code': '40.03.01', 'lvl': Specialty.EducationLevel.BACHELOR, 'form': EducationProgram.StudyForm.FULL_TIME,
                'fin': Application.FinancingType.PAID, 'status': Application.Status.SUBMITTED,
                'days_ago': 1, 'enrolled_days_ago': None, 'order_num': None,
                'scores': {'Русский язык': 74, 'Обществознание': 78, 'История': 72},
                'docs': 'partial', 'comment': 'В очереди на рассмотрение.'
            },
            # Day 0 (Today - 2 apps)
            {
                'u': 40, 'code': '09.03.01', 'lvl': Specialty.EducationLevel.BACHELOR, 'form': EducationProgram.StudyForm.FULL_TIME,
                'fin': Application.FinancingType.PAID, 'status': Application.Status.SUBMITTED,
                'days_ago': 0, 'enrolled_days_ago': None, 'order_num': None,
                'scores': {'Русский язык': 78, 'Математика (профильная)': 76, 'Информатика и ИКТ': 80},
                'docs': 'partial', 'comment': 'Подано сегодня утром.'
            },
            {
                'u': 41, 'code': '38.03.01', 'lvl': Specialty.EducationLevel.BACHELOR, 'form': EducationProgram.StudyForm.PART_TIME,
                'fin': Application.FinancingType.PAID, 'status': Application.Status.SUBMITTED,
                'days_ago': 0, 'enrolled_days_ago': None, 'order_num': None,
                'scores': {'Русский язык': 66, 'Математика (профильная)': 62, 'Обществознание': 70},
                'docs': 'partial', 'comment': 'Подано сегодня, ожидает верификации документов.'
            },
        ]

        self.stdout.write(f'Генерация {len(applications_plan)} заявлений...')

        created_apps_count = 0
        with transaction.atomic():
            for idx, plan in enumerate(applications_plan):
                applicant_user = created_users[plan['u']]
                prog = program_lookup.get((plan['code'], plan['lvl'], plan['form']))
                if not prog:
                    spec = specialty_instances.get(f"{plan['code']}_{plan['lvl']}")
                    prog = EducationProgram.objects.filter(specialty=spec).first()

                # Calculate submission datetime
                days_ago = plan['days_ago']
                hour = 9 + (idx * 3) % 9
                minute = (idx * 17) % 60
                sub_dt = now - timedelta(days=days_ago, hours=(now.hour - hour), minutes=(now.minute - minute))

                # Create application
                app = Application.objects.create(
                    applicant=applicant_user,
                    program=prog,
                    status=plan['status'],
                    financing_type=plan['fin'],
                    officer_comment=plan['comment']
                )
                Application.objects.filter(id=app.id).update(submission_date=sub_dt)

                # -------------------------------------------------------------
                # Оценки (ExamScore)
                # -------------------------------------------------------------
                for subj_name, score_val in plan['scores'].items():
                    subj_inst = subject_instances.get(subj_name)
                    if subj_inst:
                        is_verified_score = plan['status'] in [Application.Status.APPROVED, Application.Status.ENROLLED]
                        ExamScore.objects.create(
                            application=app,
                            subject=subj_inst,
                            score=score_val,
                            exam_type=ExamScore.ExamType.EGE if 'Колледж' not in prog.specialty.faculty.name else ExamScore.ExamType.INTERNAL,
                            year=2026,
                            document_number=f"77-26-{10000 + idx * 7 + random.randint(100, 999)}",
                            is_verified=is_verified_score
                        )

                # -------------------------------------------------------------
                # Документы (ApplicationDocument) с реальными тестовыми PDF
                # -------------------------------------------------------------
                docs_mode = plan['docs']
                pass_verified = (docs_mode is True) or (docs_mode == 'partial' and idx % 2 == 0)
                pass_doc = ApplicationDocument(
                    application=app,
                    document_type=ApplicationDocument.DocumentType.PASSPORT,
                    comment='Скан 2-3 стр. и регистрация' if pass_verified else 'Требуется проверка четкости скана',
                    is_verified=pass_verified
                )
                pass_doc.file.save(f"passport_{app.id}.pdf", ContentFile(SAMPLE_PDF_BYTES), save=False)
                pass_doc.save()
                ApplicationDocument.objects.filter(id=pass_doc.id).update(uploaded_at=sub_dt)

                edu_doc_type = (
                    ApplicationDocument.DocumentType.DIPLOMA
                    if plan['lvl'] == Specialty.EducationLevel.MASTER
                    else ApplicationDocument.DocumentType.CERTIFICATE
                )
                edu_verified = (docs_mode is True) or (docs_mode == 'partial' and idx % 3 != 0)
                edu_doc = ApplicationDocument(
                    application=app,
                    document_type=edu_doc_type,
                    comment='Оригинал предоставлен в приемную комиссию' if edu_verified else 'Копия загружена в ЛК',
                    is_verified=edu_verified
                )
                edu_doc.file.save(f"edu_doc_{app.id}.pdf", ContentFile(SAMPLE_PDF_BYTES), save=False)
                edu_doc.save()
                ApplicationDocument.objects.filter(id=edu_doc.id).update(uploaded_at=sub_dt + timedelta(minutes=15))

                if plan['fin'] == Application.FinancingType.BUDGET and idx % 4 == 0:
                    priv_doc = ApplicationDocument(
                        application=app,
                        document_type=ApplicationDocument.DocumentType.PRIVILEGE,
                        comment='Подтверждение особого права / квоты',
                        is_verified=docs_mode is True
                    )
                    priv_doc.file.save(f"privilege_{app.id}.pdf", ContentFile(SAMPLE_PDF_BYTES), save=False)
                    priv_doc.save()
                    ApplicationDocument.objects.filter(id=priv_doc.id).update(uploaded_at=sub_dt + timedelta(minutes=20))

                # -------------------------------------------------------------
                # Журнал аудита статусов (StatusLog) с точными датами
                # -------------------------------------------------------------
                log1 = StatusLog.objects.create(
                    application=app,
                    old_status='',
                    new_status=Application.Status.SUBMITTED,
                    changed_by=officer1,
                    comment='Заявление подано абитуриентом через личный кабинет CRM'
                )
                StatusLog.objects.filter(id=log1.id).update(changed_at=sub_dt)

                if plan['status'] == Application.Status.UNDER_REVIEW:
                    log2 = StatusLog.objects.create(
                        application=app,
                        old_status=Application.Status.SUBMITTED,
                        new_status=Application.Status.UNDER_REVIEW,
                        changed_by=officer2,
                        comment='Заявление взято в работу специалистом комиссии'
                    )
                    StatusLog.objects.filter(id=log2.id).update(changed_at=sub_dt + timedelta(hours=3))

                elif plan['status'] == Application.Status.DOCUMENTS_REQUIRED:
                    log2 = StatusLog.objects.create(
                        application=app,
                        old_status=Application.Status.SUBMITTED,
                        new_status=Application.Status.DOCUMENTS_REQUIRED,
                        changed_by=officer1,
                        comment='Запрошены читаемые копии документов'
                    )
                    StatusLog.objects.filter(id=log2.id).update(changed_at=sub_dt + timedelta(hours=4))

                elif plan['status'] in [Application.Status.APPROVED, Application.Status.ENROLLED]:
                    log_review = StatusLog.objects.create(
                        application=app,
                        old_status=Application.Status.SUBMITTED,
                        new_status=Application.Status.UNDER_REVIEW,
                        changed_by=officer1,
                        comment='Документы приняты к проверке'
                    )
                    StatusLog.objects.filter(id=log_review.id).update(changed_at=sub_dt + timedelta(hours=2))

                    log_appr = StatusLog.objects.create(
                        application=app,
                        old_status=Application.Status.UNDER_REVIEW,
                        new_status=Application.Status.APPROVED,
                        changed_by=officer1,
                        comment='Все документы верифицированы. Абитуриент допущен к участию в конкурсе'
                    )
                    StatusLog.objects.filter(id=log_appr.id).update(changed_at=sub_dt + timedelta(hours=14))

                    if plan['status'] == Application.Status.ENROLLED and plan['enrolled_days_ago'] is not None:
                        enr_days = plan['enrolled_days_ago']
                        enr_dt = now - timedelta(days=enr_days, hours=2)
                        log_enr = StatusLog.objects.create(
                            application=app,
                            old_status=Application.Status.APPROVED,
                            new_status=Application.Status.ENROLLED,
                            changed_by=admin_user,
                            comment=f"Включен в приказ о зачислении № {plan['order_num']} от {enr_dt.strftime('%d.%m.%Y')}."
                        )
                        StatusLog.objects.filter(id=log_enr.id).update(changed_at=enr_dt)

                elif plan['status'] == Application.Status.REJECTED:
                    log_rej = StatusLog.objects.create(
                        application=app,
                        old_status=Application.Status.SUBMITTED,
                        new_status=Application.Status.REJECTED,
                        changed_by=officer2,
                        comment='Отклонено: балл вступительных испытаний ниже минимального порогового значения'
                    )
                    StatusLog.objects.filter(id=log_rej.id).update(changed_at=sub_dt + timedelta(hours=6))

                elif plan['status'] == Application.Status.WITHDRAWN:
                    log_with = StatusLog.objects.create(
                        application=app,
                        old_status=Application.Status.SUBMITTED,
                        new_status=Application.Status.WITHDRAWN,
                        changed_by=officer1,
                        comment='Отозвано по личному заявлению поступающего'
                    )
                    StatusLog.objects.filter(id=log_with.id).update(changed_at=sub_dt + timedelta(days=1))

                # -------------------------------------------------------------
                # Уведомления для абитуриента (Notification)
                # -------------------------------------------------------------
                notif = Notification.objects.create(
                    user=applicant_user,
                    title=f'Заявление №{app.id} успешно зарегистрировано',
                    message=f'Ваше заявление на направление «{prog.specialty.name}» успешно принято в систему.',
                    notification_type=Notification.NotificationType.SUCCESS,
                    application=app
                )
                Notification.objects.filter(id=notif.id).update(created_at=sub_dt)

                if plan['status'] != Application.Status.SUBMITTED:
                    notif2 = Notification.objects.create(
                        user=applicant_user,
                        title=f'Обновление статуса по заявлению №{app.id}',
                        message=f'Текущий статус вашего заявления: «{app.get_status_display()}». {plan["comment"]}',
                        notification_type=Notification.NotificationType.STATUS_CHANGE,
                        application=app
                    )
                    Notification.objects.filter(id=notif2.id).update(created_at=sub_dt + timedelta(hours=14))

                created_apps_count += 1

        self.stdout.write(self.style.SUCCESS(f'Успешно создано {created_apps_count} заявлений с баллами и документами!'))

        # ---------------------------------------------------------------------
        # 9. Обращения граждан (FeedbackMessage) для KPI шапки
        # ---------------------------------------------------------------------
        FeedbackMessage.objects.all().delete()
        feedbacks_data = [
            {
                'name': 'Смирнова Татьяна Викторовна', 'phone': '+7 (916) 234-56-78', 'email': 'smirnova.tv@mail.ru',
                'subject': 'Вопрос по срокам предоставления оригинала аттестата',
                'message': 'Здравствуйте! До какого числа необходимо предоставить оригинал аттестата для зачисления на бюджет очной формы?',
                'status': FeedbackMessage.Status.RESOLVED,
                'resp': 'Оригиналы документов об образовании принимаются до 3 августа 18:00 по московскому времени.',
                'resp_by': officer1, 'days_ago': 9
            },
            {
                'name': 'Кузнецов Игорь Петрович', 'phone': '+7 (925) 345-67-89', 'email': 'kuznetsov.ip@gmail.com',
                'subject': 'Предоставление общежития для иногородних студентов',
                'message': 'Добрый день! Предоставляется ли общежитие студентам 1 курса очно-заочной формы обучения?',
                'status': FeedbackMessage.Status.RESOLVED,
                'resp': 'Общежитие в приоритетном порядке предоставляется студентам очной формы обучения. При наличии свободных мест возможно заселение студентов других форм.',
                'resp_by': officer2, 'days_ago': 7
            },
            {
                'name': 'Васильев Денис Олегович', 'phone': '+7 (903) 456-78-90', 'email': 'vasiliev.d@yandex.ru',
                'subject': 'Скидка на обучение при единовременной оплате',
                'message': 'Здравствуйте! Действует ли скидка при оплате обучения сразу за весь учебный год?',
                'status': FeedbackMessage.Status.IN_PROGRESS,
                'resp': '',
                'resp_by': None, 'days_ago': 4
            },
            {
                'name': 'Морозова Елена Сергеевна', 'phone': '+7 (915) 567-89-01', 'email': 'morozova.es@bk.ru',
                'subject': 'Перевод из другого аккредитованного университета',
                'message': 'Подскажите, пожалуйста, процедуру перевода на 2 курс направления «Экономика» из другого вуза.',
                'status': FeedbackMessage.Status.IN_PROGRESS,
                'resp': '',
                'resp_by': None, 'days_ago': 3
            },
            {
                'name': 'Попов Роман Андреевич', 'phone': '+7 (926) 678-90-12', 'email': 'popov.ra@inbox.ru',
                'subject': 'Минимальный балл по информатике на бюджет',
                'message': 'Здравствуйте! Какой был проходной балл на бюджет Прикладной информатики в прошлом году?',
                'status': FeedbackMessage.Status.NEW,
                'resp': '',
                'resp_by': None, 'days_ago': 1
            },
            {
                'name': 'Федорова Дарья Николаевна', 'phone': '+7 (916) 789-01-23', 'email': 'fedorova.dn@list.ru',
                'subject': 'Подача документов через суперсервис «Поступление в вуз онлайн»',
                'message': 'Добрый день! Видны ли в вашей CRM заявления, отправленные через Госуслуги?',
                'status': FeedbackMessage.Status.NEW,
                'resp': '',
                'resp_by': None, 'days_ago': 0
            },
        ]

        for fb_item in feedbacks_data:
            fb = FeedbackMessage.objects.create(
                full_name=fb_item['name'],
                phone=fb_item['phone'],
                email=fb_item['email'],
                subject=fb_item['subject'],
                message=fb_item['message'],
                status=fb_item['status'],
                officer_response=fb_item['resp'],
                responded_by=fb_item['resp_by'],
                responded_at=(now - timedelta(days=fb_item['days_ago'] - 1)) if fb_item['resp_by'] else None
            )
            fb_dt = now - timedelta(days=fb_item['days_ago'], hours=random.randint(2, 6))
            FeedbackMessage.objects.filter(id=fb.id).update(created_at=fb_dt)

        self.stdout.write(self.style.SUCCESS('Обращения граждан успешно сгенерированы (6 тикетов).'))

        self.stdout.write(self.style.SUCCESS(
            '\n=== [УСПЕХ] База данных наполнена реалистичными демонстрационными данными! ==='
        ))
