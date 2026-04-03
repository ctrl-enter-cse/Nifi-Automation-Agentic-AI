"""Utility to exercise NiFi agent endpoints for manual verification."""

from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / "env" / ".env")

BASE_URL = "http://localhost:8000"


def _print(name: str, status: int, payload: dict | list | str) -> None:
    print(f"{name}: {status}\n{payload}\n{'-' * 40}")


def main() -> None:
    with httpx.Client(timeout=10.0) as client:
        for path in ["/health", "/processors"]:
            response = client.get(BASE_URL + path)
            _print(path, response.status_code, response.text)

        sample_id = input("Processor ID to inspect (press enter to skip): ")
        if sample_id:
            response = client.get(f"{BASE_URL}/processors/{sample_id}")
            _print("GET /processors/{id}", response.status_code, response.text)
            if response.status_code == 200:
                action = input("Enter 'start' or 'stop' to run against the processor: ").lower()
                if action == "start":
                    response = client.post(f"{BASE_URL}/processors/{sample_id}/start")
                elif action == "stop":
                    response = client.post(f"{BASE_URL}/processors/{sample_id}/stop")
                else:
                    print("Skipping run-status change")
                    return
                _print(f"POST /processors/{sample_id}/{action}", response.status_code, response.text)


if __name__ == "__main__":
    main()
