from timetable.exports.kinds import ExporterSpec, register
from timetable.models import Employee
from timetable.services.timesheet import calculate_timesheet

 
def _approver(cycle):
    """
    Утверждающий: первый сотрудник с правом утверждения.
    TODO: заменить order_by('pk') на order_by('created_at', 'pk'),
    когда у Employee появится created_at.
    """
    return (
        Employee.objects
        .select_related("position")
        .filter(position__can_approve=True)
        .order_by("pk")
        .first()
    )


def build_context(cycle) -> dict:
    signer = cycle.compiled_by
    approver = _approver(cycle)

    return {
        "cycle_name": cycle.name.name,
        "base": cycle.base.name,
        "period_start": cycle.start_date.strftime("%d.%m.%Y"),
        "period_end": cycle.end_date.strftime("%d.%m.%Y"),
        "months": calculate_timesheet(cycle),

        "signer": signer.short_name if signer else "",
        "signer_position": signer.position.name if signer else "",

        "approver": approver.short_name if approver else "",
        "approver_position": approver.position.name if approver else "",
    }


def build_filename(cycle) -> str:
    return (
        f"timesheet_{cycle.name.name}_"
        f"{cycle.start_date:%Y-%m-%d}.docx"
    )


register(ExporterSpec(
    code="timesheet",
    name="Табель",
    sort_order=30,
    build_context=build_context,
    build_filename=build_filename,
))