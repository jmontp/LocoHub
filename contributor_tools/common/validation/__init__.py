"""Internal validation engine; rendering dependencies are loaded on demand."""
from .validator import Validator, format_validation_result


def __getattr__(name):
    if name == "ValidationReportGenerator":
        from .report_generator import ValidationReportGenerator
        return ValidationReportGenerator
    raise AttributeError(name)


__all__ = ["Validator", "format_validation_result", "ValidationReportGenerator"]
