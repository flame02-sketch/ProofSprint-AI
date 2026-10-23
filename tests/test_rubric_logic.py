import unittest

from app.rubric_logic import calculate_total_marks, validate_rubric


def make_valid_rubric():
    return {
        "exam_name": "Science Test",
        "questions": [
            {
                "question_text": "Explain photosynthesis.",
                "reference_answer": "Plants use light energy to make food.",
                "max_marks": 5,
                "criteria": [
                    {"name": "Definition", "marks": 2},
                    {"name": "Raw materials", "marks": 1},
                    {"name": "Products", "marks": 2},
                ],
            }
        ],
    }


class TestRubricLogic(unittest.TestCase):
    def test_valid_rubric_has_no_errors(self):
        self.assertEqual(validate_rubric(make_valid_rubric()), [])

    def test_total_marks_are_calculated(self):
        rubric = make_valid_rubric()
        rubric["questions"].append(
            {
                "question_text": "Define respiration.",
                "reference_answer": "The process of releasing energy.",
                "max_marks": 3,
                "criteria": [{"name": "Definition", "marks": 3}],
            }
        )

        self.assertEqual(calculate_total_marks(rubric["questions"]), 8)

    def test_missing_exam_name_is_rejected(self):
        rubric = make_valid_rubric()
        rubric["exam_name"] = ""

        self.assertIn(
            "Exam name is required.",
            validate_rubric(rubric),
        )

    def test_incorrect_criterion_total_is_rejected(self):
        rubric = make_valid_rubric()
        rubric["questions"][0]["criteria"][0]["marks"] = 1

        errors = validate_rubric(rubric)

        self.assertTrue(any("Criterion marks total" in error for error in errors))

    def test_zero_maximum_marks_is_rejected(self):
        rubric = make_valid_rubric()
        rubric["questions"][0]["max_marks"] = 0

        errors = validate_rubric(rubric)

        self.assertTrue(
            any("Maximum marks must be greater than zero" in error for error in errors)
        )


if __name__ == "__main__":
    unittest.main()
