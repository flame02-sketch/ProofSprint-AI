import json

import streamlit as st

from app.rubric_logic import calculate_total_marks, validate_rubric

st.set_page_config(
    page_title="ProofSprint AI | Rubric Builder",
    page_icon="📝",
    layout="centered",
)

st.title("ProofSprint AI")
st.header("Marking Rubric Builder")
st.write(
    "Create a marking rubric with reference answers and "
    "criteria before evaluating student responses."
)

# Keep the question count between Streamlit reruns.
if "rubric_question_count" not in st.session_state:
    st.session_state.rubric_question_count = 1

if "rubric_exam_name" not in st.session_state:
    st.session_state.rubric_exam_name = ""


st.text_input(
    "Exam or assignment name",
    key="rubric_exam_name",
    placeholder="e.g. Class 10 Science Test",
)

st.subheader("Questions")

# All widgets are outside a form. Their stable keys preserve
# entered values when Streamlit reruns after a button click.
for index in range(st.session_state.rubric_question_count):
    with st.expander(f"Question {index + 1}", expanded=True):
        st.text_area(
            "Question text",
            key=f"rubric_question_{index}",
            placeholder="Enter the complete question...",
        )

        st.number_input(
            "Maximum marks",
            min_value=1,
            max_value=1000,
            value=5,
            step=1,
            key=f"rubric_max_marks_{index}",
        )

        st.text_area(
            "Reference answer",
            key=f"rubric_reference_{index}",
            placeholder="Enter the expected answer...",
        )

        st.text_area(
            "Marking criteria (one per line)",
            key=f"rubric_criteria_{index}",
            placeholder=("Definition | 2\nRaw materials | 1\nProducts | 2"),
            help=(
                "Format: Criterion name | marks. "
                "Criterion marks must add up to the question's "
                "maximum marks."
            ),
        )

# IMPORTANT: These are ordinary buttons, not form_submit_button.
# They can safely be used because no st.form is open.
if st.button("Add another question", key="add_rubric_question"):
    st.session_state.rubric_question_count += 1
    st.rerun()


def build_rubric() -> tuple[dict, list[str]]:
    """Read form values, build the rubric, and collect validation errors."""
    errors = []
    questions = []

    exam_name = st.session_state.rubric_exam_name.strip()

    for index in range(st.session_state.rubric_question_count):
        number = index + 1

        question_text = st.session_state.get(f"rubric_question_{index}", "").strip()

        reference_answer = st.session_state.get(f"rubric_reference_{index}", "").strip()

        max_marks = st.session_state.get(f"rubric_max_marks_{index}", 5)

        criteria_text = st.session_state.get(f"rubric_criteria_{index}", "")

        criteria = []

        for line_number, raw_line in enumerate(criteria_text.splitlines(), start=1):
            line = raw_line.strip()

            if not line:
                continue

            if "|" not in line:
                errors.append(
                    f"Question {number}, line {line_number}: "
                    "Use Criterion name | marks."
                )
                continue

            name, marks_text = line.rsplit("|", maxsplit=1)
            name = name.strip()
            marks_text = marks_text.strip()

            if not name:
                errors.append(
                    f"Question {number}, line {line_number}: "
                    "Criterion name is required."
                )
                continue

            try:
                marks = float(marks_text)
            except ValueError:
                errors.append(
                    f"Question {number}, line {line_number}: Marks must be a number."
                )
                continue

            if not marks > 0 or not marks < float("inf"):
                errors.append(
                    f"Question {number}, line {line_number}: "
                    "Marks must be a positive finite number."
                )
                continue

            if marks.is_integer():
                marks = int(marks)

            criteria.append({"name": name, "marks": marks})

        questions.append(
            {
                "question_text": question_text,
                "reference_answer": reference_answer,
                "max_marks": max_marks,
                "criteria": criteria,
            }
        )

    rubric = {
        "exam_name": exam_name,
        "questions": questions,
    }

    errors.extend(validate_rubric(rubric))

    return rubric, errors


if st.button("Validate rubric", type="primary", key="validate_rubric"):
    rubric, errors = build_rubric()

    if errors:
        st.error("Please fix the following issues:")
        for error in errors:
            st.write(f"- {error}")
    else:
        total_marks = calculate_total_marks(rubric["questions"])

        st.success("Your marking rubric is valid!")
        st.metric("Total questions", len(rubric["questions"]))
        st.metric("Total marks", f"{total_marks:g}")

        st.subheader("Rubric preview")
        st.json(rubric)

        st.download_button(
            label="Download rubric as JSON",
            data=json.dumps(
                rubric,
                indent=2,
                ensure_ascii=False,
            ),
            file_name="proofsprint_rubric.json",
            mime="application/json",
        )
