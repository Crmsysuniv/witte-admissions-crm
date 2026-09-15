from django import template
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag(takes_context=True)
def render_breadcrumbs(context, custom_breadcrumbs=None):
    """
    Рендерит HTML-компонент хлебных крошек в лаконичном современном дизайне.
    """
    breadcrumbs = custom_breadcrumbs or context.get('breadcrumbs', [])
    if not breadcrumbs:
        return ''

    items_html = []
    for item in breadcrumbs:
        title = item.get('title', '')
        url = item.get('url', '#')
        is_active = item.get('is_active', False)

        if is_active:
            items_html.append(f'''
                <li class="inline-flex items-center">
                    <span class="text-sm font-semibold text-slate-800" aria-current="page">{title}</span>
                </li>
            ''')
        else:
            items_html.append(f'''
                <li class="inline-flex items-center">
                    <a href="{url}" class="text-sm font-medium text-slate-500 hover:text-indigo-600 transition-colors flex items-center gap-1.5">
                        {title}
                    </a>
                    <i class="bi bi-chevron-right text-xs text-slate-400 mx-2"></i>
                </li>
            ''')

    html = f'''
    <nav class="flex items-center text-sm" aria-label="Хлебные крошки">
        <ol class="inline-flex items-center flex-wrap gap-y-1">
            {''.join(items_html)}
        </ol>
    </nav>
    '''
    return mark_safe(html)
