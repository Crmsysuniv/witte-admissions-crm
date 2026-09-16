from django.shortcuts import render, redirect
from django.contrib import messages
from .models import FeedbackMessage
from .forms import FeedbackForm


def feedback_view(request):
    """
    Публичная страница формы обратной связи приемной комиссии МУ им. С.Ю. Витте.
    Включает валидацию полей и многоуровневую защиту от спама (honeypot + контрольный вопрос).
    """
    submitted_message = None

    if request.method == 'POST':
        form = FeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.status = FeedbackMessage.Status.NEW
            feedback.save()

            messages.success(
                request,
                f'Ваше обращение успешно зарегистрировано (№{feedback.id})! '
                'Специалист приемной комиссии подготовит ответ и свяжется с вами в течение рабочего дня.'
            )
            submitted_message = feedback
            # Reset form after successful submission
            form = FeedbackForm()
        else:
            messages.error(
                request,
                'Пожалуйста, исправьте ошибки в заполненных полях формы.'
            )
    else:
        initial_data = {}
        # Pre-fill subject if passed in URL query (e.g. ?subject=Dormitory)
        subject_param = request.GET.get('subject', '').strip()
        if subject_param:
            initial_data['subject'] = subject_param

        # Pre-fill applicant details if user is authenticated
        if request.user.is_authenticated:
            initial_data['full_name'] = request.user.get_full_name() or request.user.username
            initial_data['email'] = request.user.email
            if hasattr(request.user, 'phone') and request.user.phone:
                initial_data['phone'] = request.user.phone

        form = FeedbackForm(initial=initial_data)

    context = {
        'form': form,
        'submitted_message': submitted_message,
    }
    return render(request, 'feedback_form.html', context)
