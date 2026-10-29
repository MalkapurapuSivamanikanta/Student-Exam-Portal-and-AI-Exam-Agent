import json
from typing import Any

import requests
from google.auth import default
from google.auth.transport.requests import Request
import os
from dotenv import load_dotenv
load_dotenv()

def test_deployed_agent(
    project_id: str,
    location: str,
    reasoning_engine_id: str,
    user_id: str,
    message: dict[str, Any] | str,
) -> dict[str, Any]:
    credentials, _ = default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    credentials.refresh(Request())
    access_token = credentials.token
    message_payload = json.dumps(message) if isinstance(message, dict) else message

    base_url = (
        f"https://{location}-aiplatform.googleapis.com/v1/"
        f"projects/{project_id}/locations/{location}/"
        f"reasoningEngines/{reasoning_engine_id}"
    )

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    session_payload = {
        "class_method": "create_session",
        "input": {
            "user_id": user_id,
        },
    }

    session_response = requests.post(
        f"{base_url}:query",
        headers=headers,
        json=session_payload,
        timeout=60,
    )
    session_response.raise_for_status()

    session_id = session_response.json()["output"]["id"]
    print(f"Session created: {session_id}")

    query_payload = {
        "class_method": "async_stream_query",
        "input": {
            "user_id": user_id,
            "session_id": session_id,
            "message": message_payload,
        },
    }

    query_response = requests.post(
        f"{base_url}:streamQuery?alt=sse",
        headers=headers,
        json=query_payload,
        timeout=120,
    )
    query_response.raise_for_status()

    response_data = query_response.json()
    response = response_data.get("content", {}).get("parts", [])[0].get("text", "")
    parsed_response = json.loads(response)

    # print("\nAgent response:\n")
    # print(json.dumps(parsed_response, indent=4))
    return parsed_response


def _run_demo() -> None:
    project_id = os.getenv("PROJECT_ID")
    location = os.getenv("LOCATION")
    reasoning_engine_id = os.getenv("REASONING_ENGINE_ID")
    user_id = "testId"
    message = {
        "student_id": 1,
        "student_course": "B.Tech",
        "student_branch": "CSE",
        "chosen_subject": "Machine Learning",
    }
    response = test_deployed_agent(project_id, location, reasoning_engine_id, user_id, message)
    print(json.dumps(response, indent=4))


if __name__ == "__main__":
    _run_demo()