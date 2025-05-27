·Okay, based on the provided file structure and contents, here's a detailed project development summary for Lingualink Server:

**Project Name: Lingualink Server**

**1. Main Purpose of the Project:**

Lingualink Server is a backend service designed to provide **audio transcription and multi-language translation capabilities via a RESTful API**. It acts as an intermediary, receiving audio files from clients, processing them using an external Large Language Model (LLM) service (specifically an Omni-modal model like Qwen-VL-Max, judging by `MODEL_NAME=qwenOmni7` and the structure of `LLMService`), and returning structured text results including the original transcription and translations into specified languages. The server also includes a robust API key-based authentication system to secure its endpoints.

**2. Key Functionalities & Features:**

*   **Audio Transcription & Translation:**
    *   Accepts audio file uploads (currently `.wav` format).
    *   Validates file type and size.
    *   Encodes audio to base64 for transmission to an LLM.
    *   Constructs appropriate prompts (system and user) for the LLM.
    *   Calls an external OpenAI-compatible LLM service (e.g., vLLM serving an Omni model) to perform transcription and translation.
    *   Parses the LLM's response into a structured JSON format, separating original text and translations.
    *   Supports specifying multiple target languages for translation.
*   **RESTful API:**
    *   Built with **FastAPI**, providing high performance and automatic interactive API documentation (Swagger UI at `/docs` and ReDoc at `/redoc`).
    *   **Endpoints include:**
        *   `/api/v1/translate_audio`: Main endpoint for audio processing.
        *   `/api/v1/supported_formats`: Returns information about supported audio formats, max file size, etc.
        *   Health checks: `/api/v1/health`, `/api/v1/ping`, `/api/v1/status`.
        *   API Key Management: `/api/v1/auth/generate_key`, `/api/v1/auth/keys`, `/api/v1/auth/revoke_key`, `/api/v1/auth/update_description`, `/api/v1/auth/cleanup_expired`, `/api/v1/auth/verify`.
*   **API Key Authentication & Authorization:**
    *   Secure API access using API keys.
    *   Keys are stored in a **SQLite database** (`data/api_keys.db` by default).
    *   Supports `X-API-Key` header (recommended) and `Authorization: Bearer <key>` for authentication.
    *   Features include:
        *   API key generation (with optional name, expiration, description).
        *   Listing, revoking, and verifying API keys.
        *   Updating key descriptions.
        *   Cleaning up expired keys.
        *   **Admin Keys**: A concept of admin-privileged keys for sensitive operations like managing other keys.
    *   A dedicated `manage_api_keys.py` CLI tool for managing API keys (supports local DB operations and remote API calls to a running server).
*   **Configuration Management:**
    *   Uses `.env` files for environment-specific settings.
    *   `config/settings.py` uses Pydantic's `BaseSettings` to load and validate configurations.
    *   Configurable parameters: server host/port, debug mode, LLM service URL, model name, LLM API key, max upload size, allowed extensions, auth settings, database path, default languages/prompts.
*   **Service Management:**
    *   `manage.py`: A comprehensive CLI script for starting, stopping, restarting, checking status, and viewing logs of the server.
    *   Helper scripts (`start.sh`, `stop.sh`, `start.bat`) for convenience.
    *   `lingualink.service`: A Systemd service unit file for Linux deployments, enabling daemonization and auto-restart.
*   **Logging:**
    *   Configurable logging setup (`src/lingualink/utils/logging_config.py`).
    *   Logs to console and optionally to file (as configured by `manage.py`).
*   **Error Handling:**
    *   Custom FastAPI exception handlers for `HTTPException` and general `Exception`s, providing standardized JSON error responses.

**3. Technical Stack & Architecture:**

*   **Backend Framework:** Python 3.13+ with FastAPI.
*   **HTTP Server:** Uvicorn (used by FastAPI).
*   **Dependency Management:** `uv` (preferred), `pyproject.toml`.
*   **LLM Interaction:** `openai` Python client, configured to point to a custom vLLM endpoint.
*   **Database (API Keys):** SQLite, accessed via SQLAlchemy ORM.
*   **Configuration:** Pydantic.
*   **File Handling:** `python-multipart` for file uploads, `Werkzeug` for secure filenames.
*   **Modularity:**
    *   `src/lingualink/api/`: Defines API routers.
    *   `src/lingualink/core/`: Contains core business logic (`AudioProcessor`, `LLMService`).
    *   `src/lingualink/auth/`: Handles authentication logic (`AuthService`, FastAPI dependencies).
    *   `src/lingualink/models/`: Pydantic models for requests/responses and SQLAlchemy models for the database.
    *   `src/lingualink/utils/`: Utility functions (logging, key generation).
    *   `config/`: Application settings.

**4. Workflow for Audio Translation:**

1.  A client sends a `POST` request to `/api/v1/translate_audio` with an audio file (`.wav`), an API key in the headers, and optional `user_prompt` and `target_languages` in the form data.
2.  FastAPI, via `get_current_api_key` dependency, validates the API key using `AuthService`. If invalid, a 401/403 error is returned.
3.  The `audio_routes.translate_audio` endpoint receives the validated request.
4.  `AudioProcessor.save_upload_file()` validates the file type and size, then saves it to a temporary location.
5.  `LLMService.generate_system_prompt()` creates a system prompt based on the target languages.
6.  `LLMService.process_audio()`:
    *   Encodes the temporary audio file to a base64 string.
    *   Constructs the message payload for the LLM (system prompt, user prompt, base64 audio).
    *   Sends the request to the configured vLLM service endpoint.
    *   Receives the response from the LLM.
    *   `_parse_model_response()` parses the LLM's text output into a structured dictionary (e.g., `{"原文": "...", "英文": "...", "日文": "..."}`).
7.  The structured data is returned to the client as a JSON response.
8.  The temporary audio file is cleaned up.

**5. Development & Deployment Aspects:**

*   **Testing:** `pytest` is set up for running tests (e.g., `tests/test_auth.py`).
*   **Code Quality:** Tools like Black, iSort, Flake8 are mentioned for formatting and linting.
*   **Documentation:**
    *   Rich Markdown documentation for API usage (`API.md`), general usage (`USAGE.md`), quick start (`QUICK_START.md`), service management (`SERVICE_MANAGEMENT.md`), and authentication (`AUTHENTICATION_GUIDE.md`).
    *   Auto-generated interactive API docs via FastAPI.
*   **Deployment:**
    *   Can be run directly using `manage.py` or shell scripts.
    *   Systemd service file provided for Linux.
    *   Dockerization is outlined in `README.md` and `SERVICE_MANAGEMENT.md`, suggesting it's a planned or supported deployment method.

**In essence, Lingualink Server aims to be a self-contained, secure, and easy-to-deploy microservice that abstracts the complexities of interacting with advanced AI models for audio processing tasks, offering a simple API for developers to integrate these features into their own applications.**