from io import BytesIO
from datetime import datetime, timezone

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string

from xhtml2pdf import pisa

from backendapp.models import Case, Targets_watchlist


def _render_html_to_pdf(html: str) -> bytes:
    """Convert HTML to PDF bytes using xhtml2pdf."""
    pdf_io = BytesIO()
    pisa_status = pisa.CreatePDF(src=html, dest=pdf_io, encoding='utf-8')
    if pisa_status.err:
        return b''
    return pdf_io.getvalue()


@login_required
def download_comments_pdf_view(request, entity_type: str, entity_id):
    """Generate and download a comments-only PDF for Case or Target.

    Security:
    - Case: only the creator can download.
    - Target: allowed if requester created the target or the parent case.
    """
    entity_type = (entity_type or '').lower().strip()

    if entity_type == 'case':
        case_obj = get_object_or_404(Case, pk=entity_id, created_by=request.user)
        entity_title = case_obj.case_name
        comments = []
        if (case_obj.description or '').strip():
            comments.append({
                'author_name': case_obj.created_by.get_full_name() if hasattr(case_obj.created_by, 'get_full_name') else str(case_obj.created_by),
                'created_at': case_obj.created_at,
                'text': case_obj.description,
            })
        context = {
            'entity_type': 'Case',
            'entity_id': str(case_obj.id),
            'entity_title': entity_title,
            'generated_at': datetime.now(timezone.utc),
            'user': request.user,
            'comments': comments,
        }
    elif entity_type == 'target':
        target = get_object_or_404(Targets_watchlist, pk=entity_id)
        if (target.created_by and target.created_by != request.user) and (target.case.created_by != request.user):
            raise Http404()
        entity_title = target.target_name
        comments = []
        if (target.target_text or '').strip():
            comments.append({
                'author_name': (target.created_by.get_full_name() if target.created_by and hasattr(target.created_by, 'get_full_name') else (str(target.created_by) if target.created_by else '')),
                'created_at': target.created_at,
                'text': target.target_text,
            })
        context = {
            'entity_type': 'Target',
            'entity_id': str(target.id),
            'entity_title': entity_title,
            'generated_at': datetime.now(timezone.utc),
            'user': request.user,
            'comments': comments,
        }
    else:
        raise Http404()

    html = render_to_string('reports/comments_report.html', context)
    pdf_bytes = _render_html_to_pdf(html)
    if not pdf_bytes:
        raise Http404()

    safe_entity = 'case' if entity_type == 'case' else 'target'
    ts = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    filename = f"comments-{safe_entity}-{context['entity_id']}-{ts}.pdf"

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response






