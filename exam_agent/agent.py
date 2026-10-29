from typing import Literal

from google.adk.agents import LlmAgent
from pydantic import BaseModel, Field


class ExamInput(BaseModel):
    student_id: int = Field(description="The student's unique ID. Used only to identify the student.")
    student_course: str = Field(description="The student's course, such as B.Tech.")
    student_branch: str = Field(description="The student's branch, such as CSE or ECE.")
    chosen_subject: str = Field(
        description="The subject the student chose, such as Machine Learning or VLSI Design."
    )


class McqChoices(BaseModel):
    A: str = Field(description="Text for answer choice A.")
    B: str = Field(description="Text for answer choice B.")
    C: str = Field(description="Text for answer choice C.")
    D: str = Field(description="Text for answer choice D.")


class ExamQuestion(BaseModel):
    question: str = Field(description="The multiple-choice question.")
    mcq: McqChoices = Field(description="Exactly four answer choices labeled A through D.")
    correct_option: Literal["A", "B", "C", "D"] = Field(
        description="The label of the correct answer choice."
    )
    why_correct: str = Field(description="A concise explanation of why the answer is correct.")


class ExamOutput(BaseModel):
    questions: list[ExamQuestion] = Field(
        min_length=10,
        max_length=10,
        description="Exactly ten multiple-choice questions on the chosen subject.",
    )


root_agent = LlmAgent(
    name="exam_agent",
    model="gemini-3.5-flash",
    instruction="""
    Generate exactly 10 distinct, accurate multiple-choice exam questions for a student
    based on their chosen_subject, student_course and student_branch.

    - The questions must be about the chosen_subject. Use the student_course and
      student_branch to set the level and context (for example, a B.Tech CSE student
      choosing Machine Learning should get engineering-level questions with
      CSE-relevant applications).
    - The student_id is only an identifier. Do not use it to make assumptions about the
      student's knowledge, background or ability.
    - Use a balanced mix of foundational and applied concepts, and avoid repeating the
      same concept across questions.
    - Each question must have exactly four plausible choices labeled A, B, C and D,
      exactly one correct choice, the correct choice's label, and a concise explanation
      of why it is correct.
    - Do not include an answer key outside the structured output. Return only data
      matching the output schema.
    """,
    description=(
        "Generates a ten-question MCQ exam with answers and explanations, based on the "
        "student's chosen subject, course and branch."
    ),
    input_schema=ExamInput,
    output_schema=ExamOutput,
)