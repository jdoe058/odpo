from timetable.models import Employee


def find_approver():
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