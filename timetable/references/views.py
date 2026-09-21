import base64

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse
from django.shortcuts import render
from datetime import date

from . import export as csv_export
from . import importer as csv_import
from .registry import all_specs, get_spec


SESSION_KEY = "references_import_content"


@login_required
def exchange_view(request):
    import_result = None

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "check":
            uploaded = request.FILES.get("file")
            if uploaded is None:
                messages.error(request, "Файл не выбран.")
            else:
                content = uploaded.read()
                request.session[SESSION_KEY] = base64.b64encode(content).decode("ascii")
                import_result = csv_import.parse_and_validate(content)

        elif action == "apply":
            stored = request.session.get(SESSION_KEY)
            if not stored:
                messages.error(request, "Файл не загружен — начните заново.")
            else:
                content = base64.b64decode(stored)
                import_result = csv_import.apply(content)
                if import_result.errors:
                    messages.error(request, "Импорт не применён — есть ошибки.")
                else:
                    messages.success(request, "Импорт применён.")
                    request.session.pop(SESSION_KEY, None)

        elif action == "reset":
            request.session.pop(SESSION_KEY, None)

    return render(request, "timetable/references/exchange.html", {
        "specs": all_specs(),
        "import_result": import_result,
    })


@login_required
def export_view(request):
    content = csv_export.export_bytes()
    response = HttpResponse(content, content_type="text/csv; charset=utf-8")
    filename = f"references_{date.today():%Y-%m-%d}.csv"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@login_required
def reference_stub_view(request, slug):
    spec = get_spec(slug)
    if spec is None:
        raise Http404
    return render(request, "timetable/references/stub.html", {"spec": spec})