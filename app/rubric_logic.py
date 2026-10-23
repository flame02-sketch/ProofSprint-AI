from typing import Any


def calculate_total_marks(questions: list[dict[str, Any]]) -> float:
    """Calculate the sum of maximum marks across all questions."""
    return sum(float(question["max_marks"]) for question in questions)


def validate_rubric(rubric: dict[str, Any]) -> list[str]:
    """Return validation errors. An empty list means the rubric is valid."""
    errors: list[str] = []

    exam_name = rubric.get("exam_name", "")
    questions = rubric.get("questions", [])

    if not isinstance(exam_name, str) or not exam_name.strip():
        errors.append("Exam name is required.")

    if not isinstance(questions, list) or not questions:
        errors.append("Add at least one question.")
        return errors

    for index, question in enumerate(questions, start=1):
        prefix = f"Question {index}"

        if not isinstance(question, dict):
            errors.append(f"{prefix}: Invalid question data.")
            continue

        question_text = question.get("question_text", "")
        reference_answer = question.get("reference_answer", "")
        max_marks = question.get("max_marks")
        criteria = question.get("criteria", [])

        if not isinstance(question_text, str) or not question_text.strip():
            errors.append(f"{prefix}: Question text is required.")

        if not isinstance(reference_answer, str) or not reference_answer.strip():
            errors.append(f"{prefix}: Reference answer is required.")

        if (
            isinstance(max_marks, bool)
            or not isinstance(max_marks, (int, float))
            or max_marks <= 0
        ):
            errors.append(f"{prefix}: Maximum marks must be greater than zero.")
            continue

        if not isinstance(criteria, list) or not criteria:
            errors.append(f"{prefix}: Add at least one marking criterion.")
            continue

        criterion_total = 0.0

        for criterion_index, criterion in enumerate(criteria, start=1):
            criterion_prefix = f"{prefix}, criterion {criterion_index}"

            if not isinstance(criterion, dict):
                errors.append(f"{criterion_prefix}: Invalid criterion data.")
                continue

            name = criterion.get("name", "")
            marks = criterion.get("marks")

            if not isinstance(name, str) or not name.strip():
                errors.append(f"{criterion_prefix}: Criterion name is required.")

            if (
                isinstance(marks, bool)
                or not isinstance(marks, (int, float))
                or marks <= 0
            ):
                errors.append(f"{criterion_prefix}: Marks must be greater than zero.")
                continue

            criterion_total += float(marks)

        if abs(criterion_total - float(max_marks)) > 1e-9:
            errors.append(
                f"{prefix}: Criterion marks total {criterion_total:g}, "
                f"but maximum marks are {max_marks:g}."
            )

    return errors
