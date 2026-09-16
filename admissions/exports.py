import io
import urllib.parse
from django.http import HttpResponse, Http404
from django.utils import timezone
from django.shortcuts import get_object_or_404
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

import docx
from docx.shared import Inches, Pt, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from admissions.models import EducationProgram, Application, ApplicationDocument, Specialty


def generate_competitive_list_workbook(program, financing_type=Application.FinancingType.BUDGET, only_originals=False, is_officer=False):
    """
    Генерирует объект Workbook openpyxl с детализированным конкурсным списком
    поступающих на заданную образовательную программу.
    
    Включает:
    - Официальную шапку МУ им. С.Ю. Витте с реквизитами программы и датой выгрузки;
    - Таблицу ранжированных абитуриентов с баллами по предметам и признаком оригинала;
    - Цветовую маркировку «зеленой зоны» (попадание в контрольные цифры приема);
    - Итоговую аналитическую сводку по конкурсу и текущему проходному баллу.
    """
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Конкурсный список"
    
    # Включаем сетку таблицы
    ws.views.sheetView[0].showGridLines = True

    specialty = program.specialty
    faculty = specialty.faculty
    places_count = specialty.budget_places if financing_type == Application.FinancingType.BUDGET else specialty.paid_places
    financing_display = "Бюджетная основа" if financing_type == Application.FinancingType.BUDGET else "Платная основа (договор)"

    # Выборка заявлений
    base_qs = Application.objects.filter(
        program=program,
        financing_type=financing_type,
    ).exclude(
        status__in=[Application.Status.DRAFT, Application.Status.REJECTED, Application.Status.WITHDRAWN]
    ).select_related(
        'applicant',
        'applicant__applicant_profile',
        'program__specialty',
        'program__specialty__faculty'
    ).prefetch_related(
        'exam_scores__subject',
        'documents'
    )

    candidates = []
    for app in base_qs:
        applicant = app.applicant
        profile = getattr(applicant, 'applicant_profile', None)

        if profile and profile.snils:
            snils_display = profile.snils.strip()
        else:
            snils_display = f"№ 2026-{app.id:04d}"

        scores = list(app.exam_scores.all())
        total_score = sum(s.score for s in scores)
        
        scores_str_list = [f"{s.subject.name}: {s.score}" for s in scores]
        scores_detail = ", ".join(scores_str_list) if scores_str_list else "Баллы на проверке"

        has_original = app.documents.filter(
            document_type__in=[ApplicationDocument.DocumentType.CERTIFICATE, ApplicationDocument.DocumentType.DIPLOMA]
        ).exists()

        fio = applicant.get_full_name() or applicant.username

        candidates.append({
            'app_id': app.id,
            'fio': fio,
            'snils': snils_display,
            'total_score': total_score,
            'scores_detail': scores_detail,
            'has_original': has_original,
            'status': app.get_status_display(),
            'submission_date': app.submission_date,
        })

    # Сортировка по убыванию баллов, затем по дате подачи
    candidates.sort(key=lambda x: (-x['total_score'], x['submission_date']))

    if only_originals:
        candidates = [c for c in candidates if c['has_original']]

    # Стили шрифтов и заливок
    font_title = Font(name='Calibri', size=14, bold=True, color='0F172A')
    font_subtitle = Font(name='Calibri', size=11, bold=True, color='1E3A8A')
    font_info = Font(name='Calibri', size=10, italic=False, color='334155')
    font_header = Font(name='Calibri', size=10, bold=True, color='FFFFFF')
    font_data = Font(name='Calibri', size=10, color='1E293B')
    font_data_bold = Font(name='Calibri', size=10, bold=True, color='0F172A')
    font_summary_title = Font(name='Calibri', size=11, bold=True, color='1E3A8A')
    font_summary_label = Font(name='Calibri', size=10, bold=True, color='334155')
    font_summary_val = Font(name='Calibri', size=10, bold=True, color='0F172A')

    fill_header = PatternFill(start_color='1E3A8A', end_color='1E3A8A', fill_type='solid')
    fill_quota = PatternFill(start_color='ECFDF5', end_color='ECFDF5', fill_type='solid')      # Зеленая зона (в плане мест)
    fill_reserve = PatternFill(start_color='FFFFFF', end_color='FFFFFF', fill_type='solid')    # Резерв
    fill_zebra = PatternFill(start_color='F8FAFC', end_color='F8FAFC', fill_type='solid')      # Чередование строк
    fill_summary = PatternFill(start_color='F1F5F9', end_color='F1F5F9', fill_type='solid')    # Итоговый блок

    border_thin = Side(style='thin', color='CBD5E1')
    border_thick_bottom = Side(style='medium', color='1E3A8A')

    cell_border = Border(left=border_thin, right=border_thin, top=border_thin, bottom=border_thin)
    header_border = Border(left=border_thin, right=border_thin, top=border_thin, bottom=border_thick_bottom)

    align_center = Alignment(horizontal='center', vertical='center', wrap_text=True)
    align_left = Alignment(horizontal='left', vertical='center', wrap_text=True)

    # 1. ШАПКА ДОКУМЕНТА (Строки 1-5)
    ws['A1'] = "ЧОУ ВО «МОСКОВСКИЙ УНИВЕРСИТЕТ ИМЕНИ С.Ю. ВИТТЕ»"
    ws['A1'].font = font_title
    ws.merge_cells('A1:I1')
    ws['A1'].alignment = align_left

    ws['A2'] = "ОФИЦИАЛЬНЫЙ РАНЖИРОВАННЫЙ КОНКУРСНЫЙ СПИСОК ПОСТУПАЮЩИХ"
    ws['A2'].font = font_subtitle
    ws.merge_cells('A2:I2')
    ws['A2'].alignment = align_left

    ws['A3'] = f"Направление подготовки: {specialty.code} «{specialty.name}» ({specialty.get_education_level_display()})"
    ws['A3'].font = font_data_bold
    ws.merge_cells('A3:I3')
    ws['A3'].alignment = align_left

    ws['A4'] = f"Факультет: {faculty.name}  |  Форма обучения: {program.get_study_form_display()}  |  Основа: {financing_display}"
    ws['A4'].font = font_info
    ws.merge_cells('A4:I4')
    ws['A4'].alignment = align_left

    now_str = timezone.now().strftime('%d.%m.%Y в %H:%M')
    ws['A5'] = f"Контрольные цифры приема (план мест): {places_count}  |  Дата и время выгрузки: {now_str}"
    ws['A5'].font = font_info
    ws.merge_cells('A5:I5')
    ws['A5'].alignment = align_left

    # Строка 6 - разделитель
    ws.row_dimensions[6].height = 10

    # 2. ЗАГОЛОВКИ ТАБЛИЦЫ (Строка 7)
    headers = [
        ("№ п/п", 8, align_center),
        ("№ заявления", 14, align_center),
        ("СНИЛС / ID", 18, align_center),
        ("ФИО абитуриента", 32, align_left),
        ("Сумма баллов", 15, align_center),
        ("Предметы и баллы ЕГЭ / ВИ", 45, align_left),
        ("Оригинал аттестата", 18, align_center),
        ("Статус заявления", 24, align_center),
        ("Позиция в конкурсе", 22, align_center),
    ]

    header_row = 7
    ws.row_dimensions[header_row].height = 28

    for col_idx, (header_text, width, alignment) in enumerate(headers, start=1):
        cell = ws.cell(row=header_row, column=col_idx, value=header_text)
        cell.font = font_header
        cell.fill = fill_header
        cell.alignment = align_center
        cell.border = header_border
        
        col_letter = get_column_letter(col_idx)
        ws.column_dimensions[col_letter].width = width

    # 3. ДАННЫЕ АБИТУРИЕНТОВ (Строки 8+)
    current_row = 8
    total_candidates = len(candidates)
    originals_count = sum(1 for c in candidates if c['has_original'])

    for idx, candidate in enumerate(candidates, start=1):
        ws.row_dimensions[current_row].height = 22
        in_quota = (idx <= places_count) if places_count > 0 else False
        
        row_fill = fill_quota if in_quota else (fill_zebra if idx % 2 == 0 else fill_reserve)
        quota_label = "В зоне зачисления" if in_quota else "В резерве"
        original_label = "ДА (Оригинал)" if candidate['has_original'] else "НЕТ (Копия)"

        row_data = [
            (idx, align_center, font_data_bold if in_quota else font_data),
            (f"#{candidate['app_id']}", align_center, font_data),
            (candidate['snils'], align_center, font_data),
            (candidate['fio'], align_left, font_data_bold if in_quota else font_data),
            (candidate['total_score'], align_center, font_data_bold),
            (candidate['scores_detail'], align_left, font_data),
            (original_label, align_center, font_data_bold if candidate['has_original'] else font_data),
            (candidate['status'], align_center, font_data),
            (quota_label, align_center, font_data_bold if in_quota else font_data),
        ]

        for col_idx, (val, alignment, font_style) in enumerate(row_data, start=1):
            cell = ws.cell(row=current_row, column=col_idx, value=val)
            cell.font = font_style
            cell.fill = row_fill
            cell.alignment = alignment
            cell.border = cell_border

        current_row += 1

    # Если кандидатов нет
    if total_candidates == 0:
        ws.row_dimensions[current_row].height = 24
        cell = ws.cell(row=current_row, column=1, value="По выбранным критериям заявлений не найдено")
        ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=9)
        cell.font = font_info
        cell.alignment = align_center
        cell.border = cell_border
        current_row += 1

    # 4. ИТОГОВАЯ СВОДКА ПО КОНКУРСУ
    current_row += 1
    ws.row_dimensions[current_row].height = 12

    current_row += 1
    ws.row_dimensions[current_row].height = 24
    summary_title_cell = ws.cell(row=current_row, column=1, value="ИТОГОВЫЕ ПОКАЗАТЕЛИ КОНКУРСА:")
    summary_title_cell.font = font_summary_title
    ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=4)

    competition_ratio = round(total_candidates / places_count, 2) if places_count > 0 else 0.0
    if total_candidates > 0:
        if places_count > 0 and total_candidates >= places_count:
            passing_score = candidates[places_count - 1]['total_score']
        else:
            passing_score = candidates[-1]['total_score']
    else:
        passing_score = 0

    summary_items = [
        ("Всего заявлений в конкурсе:", f"{total_candidates} чел."),
        ("Подано оригиналов документов:", f"{originals_count} шт."),
        ("Контрольные цифры приема (мест):", f"{places_count} мест"),
        ("Конкурс на одно место:", f"{competition_ratio} чел./место"),
        ("Текущий расчетный проходной балл:", f"{passing_score} б."),
    ]

    for label, val in summary_items:
        current_row += 1
        ws.row_dimensions[current_row].height = 20
        
        c_lbl = ws.cell(row=current_row, column=1, value=label)
        c_lbl.font = font_summary_label
        c_lbl.alignment = align_left
        ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=3)

        c_val = ws.cell(row=current_row, column=4, value=val)
        c_val.font = font_summary_val
        c_val.alignment = align_left

    # Подписи ответственных лиц
    current_row += 2
    ws.row_dimensions[current_row].height = 22
    ws.cell(row=current_row, column=1, value="Ответственный секретарь приемной комиссии: ____________________ / ____________________ /").font = font_info
    ws.merge_cells(start_row=current_row, start_column=1, end_row=current_row, end_column=6)

    return wb


def export_rating_xlsx_response(program, financing_type=Application.FinancingType.BUDGET, only_originals=False, is_officer=False):
    """
    Генерирует Excel-файл и формирует HTTP-ответ с бинарным потоком .xlsx
    и правильными заголовками Content-Disposition для скачивания браузером.
    """
    wb = generate_competitive_list_workbook(
        program=program,
        financing_type=financing_type,
        only_originals=only_originals,
        is_officer=is_officer
    )

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)

    # Формируем имя файла
    spec_code_clean = program.specialty.code.replace('.', '_')
    basis_clean = "budget" if financing_type == Application.FinancingType.BUDGET else "paid"
    date_clean = timezone.now().strftime('%Y%m%d')
    filename = f"rating_{spec_code_clean}_{basis_clean}_{date_clean}.xlsx"

    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    encoded_filename = urllib.parse.quote(filename)
    response['Content-Disposition'] = f'attachment; filename="{filename}"; filename*=UTF-8\'\'{encoded_filename}'
    response['Cache-Control'] = 'no-cache'
    return response


# ============================================================================
# РАСПИСКА О ПРИЕМЕ ДОКУМЕНТОВ АБИТУРИЕНТА В ФОРМАТЕ .DOCX (PYTHON-DOCX)
# ============================================================================

def _set_cell_background(cell, fill_hex):
    """Устанавливает цвет фона ячейки таблицы DOCX."""
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), fill_hex)
    cell._tc.get_or_add_tcPr().append(shd)


def _set_cell_margins(cell, top=80, bottom=80, left=100, right=100):
    """Устанавливает внутренние отступы ячейки таблицы (в dxa, 1 pt = 20 dxa)."""
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)


def _set_table_borders(table, color="CBD5E1", sz="4", val="single"):
    """Устанавливает границы для всей таблицы."""
    tblPr = table._tbl.tblPr
    tblBorders = OxmlElement('w:tblBorders')
    for border_name in ['top', 'left', 'bottom', 'right', 'insideH', 'insideV']:
        border = OxmlElement(f'w:{border_name}')
        border.set(qn('w:val'), val)
        border.set(qn('w:sz'), sz)
        border.set(qn('w:space'), '0')
        border.set(qn('w:color'), color)
        tblBorders.append(border)
    tblPr.append(tblBorders)


def generate_application_receipt_docx(application):
    """
    Генерирует официальную расписку в приеме документов абитуриента в формате Word (.docx).
    Включает:
    - Официальный бланк МУ им. С.Ю. Витте с гербовым стилем и реквизитами;
    - Персональные и паспортные данные абитуриента, номер СНИЛС;
    - Выбранную образовательную программу, уровень, форму и основу обучения;
    - Таблицу принятых документов с видами (оригинал/копия) и статусами верификации;
    - Перечень заявленных предметов ЕГЭ и вступительных испытаний с баллами;
    - Памятку абитуриенту о сроках и процедуре зачисления;
    - Места для подписей ответственного секретаря и поступающего.
    """
    doc = docx.Document()

    # Настройка полей документа (1.5 см со всех сторон, слева 2.0 см для подшивки)
    for section in doc.sections:
        section.top_margin = Cm(1.5)
        section.bottom_margin = Cm(1.5)
        section.left_margin = Cm(2.0)
        section.right_margin = Cm(1.5)

    applicant = application.applicant
    profile = getattr(applicant, 'applicant_profile', None)
    program = application.program
    specialty = program.specialty
    faculty = specialty.faculty

    # 1. Шапка документа
    p_ministry = doc.add_paragraph()
    p_ministry.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_ministry.paragraph_format.space_before = Pt(0)
    p_ministry.paragraph_format.space_after = Pt(1)
    run_ministry = p_ministry.add_run("МИНИСТЕРСТВО НАУКИ И ВЫСШЕГО ОБРАЗОВАНИЯ РОССИЙСКОЙ ФЕДЕРАЦИИ")
    run_ministry.font.name = "Times New Roman"
    run_ministry.font.size = Pt(8.5)
    run_ministry.font.bold = True
    run_ministry.font.color.rgb = RGBColor(71, 85, 105)

    p_univ = doc.add_paragraph()
    p_univ.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_univ.paragraph_format.space_before = Pt(0)
    p_univ.paragraph_format.space_after = Pt(2)
    run_univ = p_univ.add_run("ЧОУ ВО «МОСКОВСКИЙ УНИВЕРСИТЕТ ИМЕНИ С.Ю. ВИТТЕ»")
    run_univ.font.name = "Times New Roman"
    run_univ.font.size = Pt(11.5)
    run_univ.font.bold = True
    run_univ.font.color.rgb = RGBColor(15, 23, 42)

    p_com = doc.add_paragraph()
    p_com.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_com.paragraph_format.space_before = Pt(0)
    p_com.paragraph_format.space_after = Pt(8)
    run_com = p_com.add_run("Приемная комиссия на 2026/2027 учебный год  •  Лицензия № 1618  •  Свид. об аккредитации № 3469")
    run_com.font.name = "Times New Roman"
    run_com.font.size = Pt(8.5)
    run_com.font.italic = True
    run_com.font.color.rgb = RGBColor(100, 116, 139)

    # 2. Название документа
    p_title = doc.add_paragraph()
    p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_title.paragraph_format.space_before = Pt(4)
    p_title.paragraph_format.space_after = Pt(1)
    run_title = p_title.add_run(f"РАСПИСКА В ПРИЕМЕ ДОКУМЕНТОВ № 2026-{application.id:04d}")
    run_title.font.name = "Times New Roman"
    run_title.font.size = Pt(12.5)
    run_title.font.bold = True
    run_title.font.color.rgb = RGBColor(30, 58, 138)

    sub_date = application.submission_date.strftime('%d.%m.%Y в %H:%M') if application.submission_date else timezone.now().strftime('%d.%m.%Y')
    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sub.paragraph_format.space_before = Pt(0)
    p_sub.paragraph_format.space_after = Pt(8)
    run_sub = p_sub.add_run(f"к заявлению о приеме на обучение от {sub_date}")
    run_sub.font.name = "Times New Roman"
    run_sub.font.size = Pt(9.5)
    run_sub.font.italic = True

    # 3. Сведения об абитуриенте
    p_sec1 = doc.add_paragraph()
    p_sec1.paragraph_format.space_before = Pt(4)
    p_sec1.paragraph_format.space_after = Pt(2)
    run_sec1 = p_sec1.add_run("1. Сведения о поступающем:")
    run_sec1.font.name = "Times New Roman"
    run_sec1.font.size = Pt(10)
    run_sec1.font.bold = True
    run_sec1.font.color.rgb = RGBColor(15, 23, 42)

    fio = applicant.get_full_name() or applicant.username
    snils = profile.snils if (profile and profile.snils) else f"№ 2026-{application.id:04d}"
    
    passport_str = "—"
    if profile and (profile.passport_series or profile.passport_number):
        p_issue = profile.passport_issue_date.strftime('%d.%m.%Y') if profile.passport_issue_date else ''
        p_code = f" (код подр. {profile.passport_department_code})" if profile.passport_department_code else ''
        passport_str = f"Паспорт гражданина РФ: {profile.passport_series or ''} {profile.passport_number or ''}, выдан {p_issue} {profile.passport_issued_by or ''}{p_code}"

    phone_str = applicant.phone or '—'
    email_str = applicant.email or '—'
    address_str = profile.address if (profile and profile.address) else '—'

    t_info = doc.add_table(rows=5, cols=2)
    t_info.alignment = WD_TABLE_ALIGNMENT.CENTER
    _set_table_borders(t_info, color="E2E8F0", sz="4")

    info_rows = [
        ("Фамилия, Имя, Отчество:", fio),
        ("Идентификатор / СНИЛС:", snils),
        ("Документ, удост. личность:", passport_str),
        ("Контактные данные:", f"Телефон: {phone_str}  |  Email: {email_str}"),
        ("Адрес регистрации / проживания:", address_str),
    ]

    for idx, (label, value) in enumerate(info_rows):
        row = t_info.rows[idx]
        _set_cell_background(row.cells[0], "F8FAFC")
        _set_cell_margins(row.cells[0], top=40, bottom=40, left=80, right=80)
        _set_cell_margins(row.cells[1], top=40, bottom=40, left=80, right=80)
        
        p0 = row.cells[0].paragraphs[0]
        p0.paragraph_format.space_before = Pt(0)
        p0.paragraph_format.space_after = Pt(0)
        r0 = p0.add_run(label)
        r0.font.name = "Times New Roman"
        r0.font.size = Pt(8.5)
        r0.font.bold = True
        row.cells[0].width = Inches(2.2)

        p1 = row.cells[1].paragraphs[0]
        p1.paragraph_format.space_before = Pt(0)
        p1.paragraph_format.space_after = Pt(0)
        r1 = p1.add_run(value)
        r1.font.name = "Times New Roman"
        r1.font.size = Pt(8.5)
        row.cells[1].width = Inches(4.8)

    # 4. Выбранные условия поступления
    p_sec2 = doc.add_paragraph()
    p_sec2.paragraph_format.space_before = Pt(6)
    p_sec2.paragraph_format.space_after = Pt(2)
    run_sec2 = p_sec2.add_run("2. Выбранная образовательная программа и условия обучения:")
    run_sec2.font.name = "Times New Roman"
    run_sec2.font.size = Pt(10)
    run_sec2.font.bold = True
    run_sec2.font.color.rgb = RGBColor(15, 23, 42)

    t_prog = doc.add_table(rows=4, cols=2)
    t_prog.alignment = WD_TABLE_ALIGNMENT.CENTER
    _set_table_borders(t_prog, color="E2E8F0", sz="4")

    prog_rows = [
        ("Направление подготовки / Специальность:", f"{specialty.code} «{specialty.name}» ({specialty.get_education_level_display()})"),
        ("Факультет / Институт:", faculty.name),
        ("Форма и нормативный срок обучения:", f"{program.get_study_form_display()} форма  •  {program.duration}"),
        ("Основа финансирования и статус:", f"{application.get_financing_type_display()}  •  Статус: {application.get_status_display()}"),
    ]

    for idx, (label, value) in enumerate(prog_rows):
        row = t_prog.rows[idx]
        _set_cell_background(row.cells[0], "F8FAFC")
        _set_cell_margins(row.cells[0], top=40, bottom=40, left=80, right=80)
        _set_cell_margins(row.cells[1], top=40, bottom=40, left=80, right=80)

        p0 = row.cells[0].paragraphs[0]
        p0.paragraph_format.space_before = Pt(0)
        p0.paragraph_format.space_after = Pt(0)
        r0 = p0.add_run(label)
        r0.font.name = "Times New Roman"
        r0.font.size = Pt(8.5)
        r0.font.bold = True
        row.cells[0].width = Inches(2.2)

        p1 = row.cells[1].paragraphs[0]
        p1.paragraph_format.space_before = Pt(0)
        p1.paragraph_format.space_after = Pt(0)
        r1 = p1.add_run(value)
        r1.font.name = "Times New Roman"
        r1.font.size = Pt(8.5)
        row.cells[1].width = Inches(4.8)

    # 5. Перечень принятых документов
    p_sec3 = doc.add_paragraph()
    p_sec3.paragraph_format.space_before = Pt(6)
    p_sec3.paragraph_format.space_after = Pt(2)
    run_sec3 = p_sec3.add_run("3. Перечень принятых документов и материалов:")
    run_sec3.font.name = "Times New Roman"
    run_sec3.font.size = Pt(10)
    run_sec3.font.bold = True
    run_sec3.font.color.rgb = RGBColor(15, 23, 42)

    doc_entries = [
        ("Электронное заявление о приеме на обучение", "Оригинал (ЛК/ЭЦП)", f"№ 2026-{application.id:04d}", "Зарегистрировано"),
        ("Документ, удостоверяющий личность (Паспорт РФ)", "Скан-копия", f"серия {profile.passport_series or '—'} № {profile.passport_number or '—'}" if profile else "Данные внесены", "Принято"),
    ]

    if profile and profile.snils:
        doc_entries.append((
            "Страховое свидетельство пенсионного страхования (СНИЛС)",
            "Сведения / копия",
            profile.snils,
            "ФИС ГИА"
        ))

    for doc_item in application.documents.all():
        doc_type_name = doc_item.get_document_type_display()
        doc_kind = "Оригинал / скан" if doc_item.document_type in [ApplicationDocument.DocumentType.CERTIFICATE, ApplicationDocument.DocumentType.DIPLOMA] else "Скан-копия"
        v_status = "Верифицирован" if doc_item.is_verified else "На проверке"
        doc_entries.append((
            doc_type_name,
            doc_kind,
            f"Загружен {doc_item.uploaded_at.strftime('%d.%m.%Y')}",
            v_status
        ))

    t_docs = doc.add_table(rows=len(doc_entries) + 1, cols=5)
    t_docs.alignment = WD_TABLE_ALIGNMENT.CENTER
    _set_table_borders(t_docs, color="CBD5E1", sz="4")

    doc_headers = ["№", "Наименование документа", "Вид предоставления", "Реквизиты / Дата", "Отметка комиссии"]
    doc_widths = [Inches(0.4), Inches(2.8), Inches(1.4), Inches(1.3), Inches(1.1)]

    header_row = t_docs.rows[0]
    for col_idx, (h_text, width) in enumerate(zip(doc_headers, doc_widths)):
        cell = header_row.cells[col_idx]
        _set_cell_background(cell, "1E3A8A")
        _set_cell_margins(cell, top=60, bottom=60, left=50, right=50)
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        r = p.add_run(h_text)
        r.font.name = "Times New Roman"
        r.font.size = Pt(8)
        r.font.bold = True
        r.font.color.rgb = RGBColor(255, 255, 255)
        cell.width = width

    for row_idx, (d_name, d_kind, d_req, d_stat) in enumerate(doc_entries, start=1):
        row = t_docs.rows[row_idx]
        row_cells = [str(row_idx), d_name, d_kind, d_req, d_stat]
        bg_color = "FFFFFF" if row_idx % 2 != 0 else "F8FAFC"
        
        for col_idx, (text_val, width) in enumerate(zip(row_cells, doc_widths)):
            cell = row.cells[col_idx]
            _set_cell_background(cell, bg_color)
            _set_cell_margins(cell, top=40, bottom=40, left=50, right=50)
            p = cell.paragraphs[0]
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            if col_idx in [0, 2, 4]:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            else:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            
            r = p.add_run(text_val)
            r.font.name = "Times New Roman"
            r.font.size = Pt(8)
            if col_idx == 4 and "Верифицирован" in text_val:
                r.font.bold = True
                r.font.color.rgb = RGBColor(16, 149, 117)
            cell.width = width

    # 6. Вступительные баллы и ЕГЭ
    scores_list = list(application.exam_scores.all())
    if scores_list:
        p_sec4 = doc.add_paragraph()
        p_sec4.paragraph_format.space_before = Pt(6)
        p_sec4.paragraph_format.space_after = Pt(2)
        run_sec4 = p_sec4.add_run("4. Зачтенные результаты ЕГЭ и вступительных испытаний:")
        run_sec4.font.name = "Times New Roman"
        run_sec4.font.size = Pt(10)
        run_sec4.font.bold = True
        run_sec4.font.color.rgb = RGBColor(15, 23, 42)

        t_scores = doc.add_table(rows=len(scores_list) + 2, cols=5)
        t_scores.alignment = WD_TABLE_ALIGNMENT.CENTER
        _set_table_borders(t_scores, color="CBD5E1", sz="4")

        score_headers = ["№", "Предмет вступительного испытания", "Форма сдачи", "Мин. балл", "Набранный балл"]
        score_widths = [Inches(0.4), Inches(3.2), Inches(1.4), Inches(1.0), Inches(1.0)]

        h_score_row = t_scores.rows[0]
        for col_idx, (h_text, width) in enumerate(zip(score_headers, score_widths)):
            cell = h_score_row.cells[col_idx]
            _set_cell_background(cell, "1E3A8A")
            _set_cell_margins(cell, top=60, bottom=60, left=50, right=50)
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            r = p.add_run(h_text)
            r.font.name = "Times New Roman"
            r.font.size = Pt(8)
            r.font.bold = True
            r.font.color.rgb = RGBColor(255, 255, 255)
            cell.width = width

        total_sc = 0
        for s_idx, score_obj in enumerate(scores_list, start=1):
            total_sc += score_obj.score
            s_row = t_scores.rows[s_idx]
            s_cells = [
                str(s_idx),
                score_obj.subject.name,
                score_obj.get_exam_type_display(),
                str(score_obj.subject.min_score),
                f"{score_obj.score} б."
            ]
            for col_idx, (text_val, width) in enumerate(zip(s_cells, score_widths)):
                cell = s_row.cells[col_idx]
                _set_cell_margins(cell, top=40, bottom=40, left=50, right=50)
                p = cell.paragraphs[0]
                p.paragraph_format.space_before = Pt(0)
                p.paragraph_format.space_after = Pt(0)
                if col_idx in [0, 2, 3, 4]:
                    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                else:
                    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                r = p.add_run(text_val)
                r.font.name = "Times New Roman"
                r.font.size = Pt(8)
                if col_idx == 4:
                    r.font.bold = True
                cell.width = width

        # Строка итоговой суммы
        tot_row = t_scores.rows[-1]
        _set_cell_background(tot_row.cells[0], "F1F5F9")
        _set_cell_background(tot_row.cells[4], "ECFDF5")
        
        tot_row.cells[0].merge(tot_row.cells[3])
        p_tot_lbl = tot_row.cells[0].paragraphs[0]
        p_tot_lbl.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p_tot_lbl.paragraph_format.space_before = Pt(0)
        p_tot_lbl.paragraph_format.space_after = Pt(0)
        r_tot_lbl = p_tot_lbl.add_run("ИТОГОВАЯ СУММА КОНКУРСНЫХ БАЛЛОВ:")
        r_tot_lbl.font.name = "Times New Roman"
        r_tot_lbl.font.size = Pt(8.5)
        r_tot_lbl.font.bold = True

        p_tot_val = tot_row.cells[4].paragraphs[0]
        p_tot_val.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_tot_val.paragraph_format.space_before = Pt(0)
        p_tot_val.paragraph_format.space_after = Pt(0)
        r_tot_val = p_tot_val.add_run(f"{total_sc} б.")
        r_tot_val.font.name = "Times New Roman"
        r_tot_val.font.size = Pt(9)
        r_tot_val.font.bold = True
        r_tot_val.font.color.rgb = RGBColor(16, 149, 117)

    # 7. Памятка поступающему
    p_memo = doc.add_paragraph()
    p_memo.paragraph_format.space_before = Pt(6)
    p_memo.paragraph_format.space_after = Pt(1)
    run_memo = p_memo.add_run("5. Памятка для поступающего:")
    run_memo.font.name = "Times New Roman"
    run_memo.font.size = Pt(9)
    run_memo.font.bold = True

    notes = [
        "1. Позиция в конкурсных списках обновляется в реальном времени на портале CRM университета (раздел «Рейтинг»).",
        "2. Для зачисления на бюджетные места оригинал документа об образовании необходимо предоставить в комиссию не позднее 12:00 (мск) дня завершения приема оригиналов.",
        "3. Контакты приемной комиссии: 115432, г. Москва, 2-й Кожуховский проезд, д. 12, стр. 1. Тел.: +7 (495) 500-03-63, Email: priem@witte.ru.",
    ]
    for note in notes:
        p_n = doc.add_paragraph()
        p_n.paragraph_format.space_before = Pt(0)
        p_n.paragraph_format.space_after = Pt(0)
        r_n = p_n.add_run(note)
        r_n.font.name = "Times New Roman"
        r_n.font.size = Pt(7.5)
        r_n.font.color.rgb = RGBColor(71, 85, 105)

    # 8. Подписи
    p_sign_sp = doc.add_paragraph()
    p_sign_sp.paragraph_format.space_before = Pt(6)
    p_sign_sp.paragraph_format.space_after = Pt(1)

    t_signs = doc.add_table(rows=1, cols=2)
    t_signs.alignment = WD_TABLE_ALIGNMENT.CENTER
    _set_table_borders(t_signs, color="FFFFFF", sz="0", val="none")

    cell_officer = t_signs.rows[0].cells[0]
    cell_officer.width = Inches(3.5)
    p_off = cell_officer.paragraphs[0]
    p_off.paragraph_format.space_before = Pt(0)
    p_off.paragraph_format.space_after = Pt(1)
    r_off = p_off.add_run("Документы и заявление принял:\nСпециалист приемной комиссии:\n\n__________________ / __________________ /")
    r_off.font.name = "Times New Roman"
    r_off.font.size = Pt(8)

    cell_app = t_signs.rows[0].cells[1]
    cell_app.width = Inches(3.5)
    p_ap = cell_app.paragraphs[0]
    p_ap.paragraph_format.space_before = Pt(0)
    p_ap.paragraph_format.space_after = Pt(1)
    r_ap = p_ap.add_run(f"Расписку получил, с Правилами приема ознакомлен:\nПоступающий:\n\n__________________ / {fio} /")
    r_ap.font.name = "Times New Roman"
    r_ap.font.size = Pt(8)

    return doc


def export_receipt_docx_response(application):
    """
    Генерирует документ расписки в формате Word (.docx) и возвращает HTTP-ответ
    со всеми необходимыми MIME-типами и заголовками скачивания файла.
    """
    doc = generate_application_receipt_docx(application)

    buffer = io.BytesIO()
    doc.save(buffer)
    buffer.seek(0)

    filename = f"receipt_app_{application.id}_{timezone.now().strftime('%Y%m%d')}.docx"
    encoded_filename = urllib.parse.quote(filename)

    response = HttpResponse(
        buffer.getvalue(),
        content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )
    response['Content-Disposition'] = f'attachment; filename="{filename}"; filename*=UTF-8\'\'{encoded_filename}'
    response['Cache-Control'] = 'no-cache'
    return response
