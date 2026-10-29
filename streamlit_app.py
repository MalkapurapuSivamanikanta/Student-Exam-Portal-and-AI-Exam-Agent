import logging
import os
import sys
from pathlib import Path
from typing import Any

import psycopg2
import requests
import streamlit as st
from dotenv import load_dotenv
from google.auth.exceptions import GoogleAuthError

load_dotenv()

from test_deployed import test_deployed_agent
from students_service import StudentService


st.set_page_config(page_title="Student Exam Agent", page_icon="🧠", layout="wide")

PROJECT_ID = os.getenv("PROJECT_ID", "tactical-curve-512912-k2")
LOCATION = os.getenv("LOCATION", "asia-south1")
REASONING_ENGINE_ID = os.getenv("REASONING_ENGINE_ID", "")


@st.cache_data(show_spinner=False)
def fetch_questions(student_id: int, student_course: str, student_branch: str, chosen_subject: str) -> list[dict[str, Any]]:
    payload = {
        "student_id": student_id,
        "student_course": student_course,
        "student_branch": student_branch,
        "chosen_subject": chosen_subject,
    }
    response = test_deployed_agent(
        project_id=PROJECT_ID,
        location=LOCATION,
        reasoning_engine_id=REASONING_ENGINE_ID,
        user_id=str(student_id),
        message=payload,
    )
    return response.get("questions", [])


if "student_authenticated" not in st.session_state:
    st.session_state.student_authenticated = False
if "student" not in st.session_state:
    st.session_state.student = {}
if "exam_started" not in st.session_state:
    st.session_state.exam_started = False
if "questions" not in st.session_state:
    st.session_state.questions = []
if "answers" not in st.session_state:
    st.session_state.answers = {}
if "current_index" not in st.session_state:
    st.session_state.current_index = 0
if "exam_submitted" not in st.session_state:
    st.session_state.exam_submitted = False
if "exam_score" not in st.session_state:
    st.session_state.exam_score = 0


def start_exam() -> None:
    try:
        student = StudentService().keep_exam_for_student(
            st.session_state.id_card_no,
            st.session_state.login_password,
        )
    except psycopg2.Error:
        st.error("Unable to retrieve your exam details. Please try again later.")
        return

    if student is None:
        st.session_state.student_authenticated = False
        st.error("Invalid login ID or password. Please sign in again.")
        return

    if student.get("written_exam"):
        st.session_state.student = student
        return

    chosen_subject = student.get("chosen_subject")
    if not chosen_subject:
        st.error("No examination subject is configured for this student.")
        return

    try:
        questions = fetch_questions(
            student["student_id"],
            student["student_course"],
            student["student_branch"],
            chosen_subject,
        )
    except (GoogleAuthError, requests.RequestException):
        logging.exception("Failed to generate exam from the deployed agent")
        st.error("Unable to generate the exam right now. Please try again.")
        return

    if not questions:
        st.error("The exam service did not return any questions. Please try again.")
        return

    st.session_state.student = student
    st.session_state.questions = questions
    st.session_state.answers = {}
    st.session_state.current_index = 0
    st.session_state.exam_submitted = False
    st.session_state.exam_started = True
    del st.session_state.id_card_no
    del st.session_state.login_password


if st.session_state.exam_submitted:
    questions = st.session_state.questions

    st.title("Exam Results")
    st.success(f"Exam submitted. Your score: {st.session_state.exam_score}/{len(questions)}")
    st.subheader("Review")
    for idx, question in enumerate(questions, start=1):
        student_choice = st.session_state.answers.get(str(idx - 1))
        correct = question["correct_option"]
        status = "✅ Correct" if student_choice == correct else "❌ Incorrect"
        st.markdown(f"### Q{idx}: {question['question']}")
        st.write(f"Your answer: {student_choice or 'Not answered'}")
        st.write(f"Correct answer: {correct}")
        st.write(f"Explanation: {question['why_correct']}")
        st.write(status)
        st.write("---")

    st.stop()


if not st.session_state.student_authenticated:
    st.title("Student Login")
    with st.form("student_details"):
        id_card_no = st.text_input("Login ID (ID card number)")
        login_password = st.text_input("Password", type="password")
        login_submitted = st.form_submit_button("Login")

    if login_submitted:
        if not id_card_no.strip() or not login_password:
            st.error("Enter both your login ID and password.")
        else:
            try:
                student = StudentService().find_student_by_login(
                    id_card_no.strip(),
                    login_password,
                )
            except psycopg2.Error:
                st.error("Unable to verify your login right now. Please try again later.")
            else:
                if student is None:
                    st.error("Invalid login ID or password.")
                else:
                    st.session_state.student = student
                    st.session_state.id_card_no = id_card_no.strip()
                    st.session_state.login_password = login_password
                    st.session_state.student_authenticated = True
                    st.rerun()

    st.stop()

if not st.session_state.exam_started:
    student = st.session_state.student

    if student.get("written_exam"):
        st.title("Exam Already Completed")
        st.info("You have already written this exam. Another attempt is not available.")
        if student.get("exam_score") is not None:
            st.success(f"Your saved score: {student['exam_score']}/10")
        st.stop()

    chosen_subject = student.get("chosen_subject")

    st.title("Student Exam")
    st.write(f"Welcome, {student.get('student_name', 'student')}.")
    if chosen_subject:
        st.subheader(f"Examination: {chosen_subject}")
    else:
        st.error("No examination subject is configured for this student.")

    if chosen_subject and st.button("Start Exam"):
        with st.spinner("Generating your exam..."):
            start_exam()
        if st.session_state.exam_started or st.session_state.student.get("written_exam"):
            st.rerun()

    st.stop()


questions = st.session_state.questions
current_index = st.session_state.current_index
current_question = questions[current_index]

st.title(f"Question {current_index + 1} of {len(questions)}")
st.subheader(current_question["question"])

options = ["A", "B", "C", "D"]
selected = st.radio(
    "Choose one option",
    options,
    format_func=lambda option: f"{option}. {current_question['mcq'][option]}",
    index=None,
    key=f"q_{current_index}",
    horizontal=False,
)

if selected:
    st.session_state.answers[str(current_index)] = selected

col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    if current_index > 0 and st.button("Previous"):
        st.session_state.current_index -= 1
        st.rerun()

with col2:
    if current_index < len(questions) - 1 and st.button("Next"):
        st.session_state.current_index += 1
        st.rerun()

with col3:
    if current_index == len(questions) - 1 and st.button("Submit Exam"):
        score = 0
        for index, q in enumerate(questions):
            correct = q["correct_option"]
            student_choice = st.session_state.answers.get(str(index))
            if student_choice == correct:
                score += 1

        try:
            result = StudentService().update_student_exam_score(
                st.session_state.student["student_id"],
                score,
            )
        except psycopg2.Error:
            st.error("Unable to save your exam score. Please try submitting again.")
        else:
            if "error" in result:
                st.error(result["error"])
            else:
                st.session_state.exam_score = score
                st.session_state.exam_submitted = True
                st.rerun()
