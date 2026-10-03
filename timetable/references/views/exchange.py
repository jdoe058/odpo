"""Обмен справочниками: выгрузка и импорт XLSX."""
import base64

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from datetime import date

from timetable.references import xlsx_export
from timetable.references import xlsx_importer
from timetable.references.forms import ReferenceImportForm
from timetable.references.registry import specs_in_import_order


SESSION_KEY = "references_import_content"


@login_required
def exchange_view(request):
    import_result = None
    form = ReferenceImportForm()

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "check":
            form = ReferenceImportForm(request.POST, request.FILES)
            if form.is_valid():
                content = form.cleaned_data["file"].read()
                request.session[SESSION_KEY] = base64.b64encode(content).decode("ascii")
                import_result = xlsx_importer.parse_and_validate(content)

        elif action == "apply":
            stored = request.session.get(SESSION_KEY)
            if not stored:
                messages.error(request, "Файл не загружен — начните заново.")
            else:
                content = base64.b64decode(stored)
                import_result = xlsx_importer.apply(content)
                if import_result.errors:
                    messages.error(request, "Импорт не применён — есть ошибки.")
                else:
                    messages.success(request, "Импорт применён.")
                    request.session.pop(SESSION_KEY, None)

        elif action == "reset":
            request.session.pop(SESSION_KEY, None)

    return render(request, "timetable/references/exchange.html", {
        "specs": specs_in_import_order(),
        "form": form,
        "import_result": import_result,
    })


@login_required
def export_view(request):
    content = xlsx_export.references_to_xlsx_bytes()
    response = HttpResponse(
        content,
        content_type=(
            "application/vnd.openxmlformats-officedocument"
            ".spreadsheetml.sheet"
        ),
    )
    filename = f"references_{date.today():%Y-%m-%d}.xlsx"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response