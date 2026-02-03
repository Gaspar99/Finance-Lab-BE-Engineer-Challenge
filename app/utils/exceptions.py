class InvalidFileError(Exception):
    """Raised when the uploaded file is not a valid PDF or exceeds size limit."""
    pass


class ExtractionError(Exception):
    """Raised when Document AI fails to process the PDF."""
    pass


class StorageError(Exception):
    """Raised when an image upload to GCS fails."""
    pass


class FirestoreError(Exception):
    """Raised when a read or write operation to Firestore fails."""
    pass


class ReportNotFoundError(Exception):
    """Raised when a report ID does not exist in Firestore."""
    pass
