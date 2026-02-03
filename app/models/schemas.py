from app.models.report import Report


class UploadResponse(Report):
    """Response returned after a successful POST /reports."""
    pass


class ReportResponse(Report):
    """Response returned by GET /reports/{id}."""
    pass


class ErrorResponse(Report):
    """Response returned when the pipeline fails."""
    pass
