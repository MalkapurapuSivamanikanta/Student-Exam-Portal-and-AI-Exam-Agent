import os
from contextlib import contextmanager
from typing import Any, Generator

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()


class StudentService:
    """Plain class with functions for student database operations."""

    def __init__(self) -> None:
        # Read credentials from environment variables, not source code
        self.db_config = {
            "user": os.getenv("DB_USER", "postgres"),
            "password": os.getenv("DB_PASSWORD"),
            "host": os.getenv("DB_HOST", "localhost"),
            "port": os.getenv("DB_PORT", "5432"),
            "database": os.getenv("DB_NAME", "postgres"),
        }

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------
    @contextmanager
    def get_db_connection(self) -> Generator[Any, None, None]:
        """Open a connection; commit on success, rollback on error, always close."""
        conn = None
        try:
            conn = psycopg2.connect(**self.db_config)
            yield conn
            conn.commit()
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"Database error: {e}")
            raise
        finally:
            if conn:
                conn.close()

    def _fetch_one(self, query: str, params: tuple) -> dict[str, Any] | None:
        with self.get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                return cursor.fetchone()

    def _fetch_all(self, query: str, params: tuple = ()) -> list[dict[str, Any]]:
        with self.get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params)
                return cursor.fetchall()

    # ------------------------------------------------------------------
    # Functions
    # ------------------------------------------------------------------
    def find_student_by_id(self, student_id: int) -> dict[str, Any] | None:
        """Find a student by their unique ID."""
        query = "SELECT * FROM students_info WHERE student_id = %s;"
        try:
            return self._fetch_one(query, (student_id,))
        except Exception as e:
            print(f"Error fetching student by ID: {e}")
            return None

    def find_student_by_id_card(self, id_card_no: str) -> dict[str, Any] | None:
        """Find a student by their ID card number."""
        query = """
            SELECT s.*
            FROM students_info s
            JOIN student_login l ON s.student_id = l.student_id
            WHERE s.id_card_no = %s AND l.is_active = TRUE;
        """
        try:
            return self._fetch_one(query, (id_card_no,))
        except Exception as e:
            print(f"Error fetching student by ID card number: {e}")
            return None

    def find_student_by_login(
        self, id_card_no: str, login_password: str
    ) -> dict[str, Any] | None:
        """Find a student by their ID card number and login password."""
        query = """
            SELECT s.*
            FROM students_info s
            JOIN student_login l ON s.student_id = l.student_id
            WHERE s.id_card_no = %s
              AND l.login_password = %s
              AND l.is_active = TRUE;
        """
        return self._fetch_one(query, (id_card_no, login_password))

    def keep_exam_for_student(
        self, id_card_no: str, login_password: str
    ) -> dict[str, Any] | None:
        """Get exam details and completion status after login check."""
        query = """
            SELECT s.student_id, s.student_name, s.student_course, s.student_branch,
                   s.chosen_subject, s.written_exam, s.exam_score
            FROM students_info s
            JOIN student_login l ON s.student_id = l.student_id
            WHERE s.id_card_no = %s
              AND l.login_password = %s
              AND l.is_active = TRUE;
        """
        return self._fetch_one(query, (id_card_no, login_password))

    def get_all_student_details(self) -> list[dict[str, Any]]:
        """Get all student details without login passwords."""
        query = """
            SELECT s.*
            FROM students_info AS s
            ORDER BY s.student_id;
        """
        try:
            return self._fetch_all(query)
        except Exception as e:
            print(f"Failed to fetch student details: {e}")
            return []

    def update_student_exam_score(
        self, student_id: int, exam_score: float
    ) -> dict[str, Any]:
        """Set a student's exam score (0-10) and mark the exam as written."""
        if not 0 <= exam_score <= 10:
            raise ValueError("exam_score must be between 0 and 10.")

        query = """
            UPDATE students_info
            SET written_exam = 1, exam_score = %s
            WHERE student_id = %s AND written_exam = 0
            RETURNING student_id, student_name, written_exam, exam_score;
        """
        try:
            updated_student = self._fetch_one(query, (exam_score, student_id))
            if updated_student is None:
                return {
                    "error": (
                        f"No student found with ID {student_id}, or the exam "
                        "has already been submitted."
                    )
                }
            return updated_student
        except Exception as e:
            print(f"Error updating student exam score: {e}")
            return {"error": "Failed to update student exam score."}


if __name__ == "__main__":
    service = StudentService()
    print(service.find_student_by_id(1))