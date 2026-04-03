# Claude Context: NiFi AI Agent Architecture

This document serves as the "AI Memory" for this project. It explains the core logic, design decisions, and extension patterns for any AI model (like Claude) interacting with the codebase.

---

## 🏗️ Core Logic Summary

### 1. The Async Flow Integration
The project is built on **`asyncio`** and **`httpx`**. 
*   **Protocol**: All interactions with NiFi are asynchronous. 
*   **Tooling**: Use `await _request(...)` for all API calls to ensure scalability.
*   **Security**: Authentication is managed by a Bearer token stored in a global variable in `nifi_client.py`. If a 401 is received, it automatically clears the token and retries once.

### 2. Revision Management (Critical)
NiFi uses **optimistic locking**. Every modification MUST include the current revision.
```python
# The pattern for all updates:
revision = await _get_revision(processor_id)
payload = { "revision": revision, "component": { ... } }
await _request("PUT", url, json=payload)
```
*   **Failure Mode**: If you omit `revision`, NiFi will reject the update with a 409 conflict.

### 3. The "Brain" (Flow Generator Logic)
The `flow_generator.py` uses a **"Blueprint-first"** approach.
*   **Strategy**: It converts a `curl` command into a logic tree.
*   **Key Heuristic**: If `curl --data` exists, it MUST insert an `EvaluateJsonPath` processor between the `HttpRequest` and `InvokeHTTP` to parse common JSON fields into flowfile attributes.
*   **Port Mapping**: It defaults to port `7808` for the `HandleHttpRequest` processor.

---

## 🧠 Extension Guidelines (How to add features)

If asked to add a new "Processor Type" or "Automation Script":
1.  **Add to `nifi_client.py`**: Create the low-level `create_...` or `update_...` function first.
2.  **Add to `scripts/`**: Create a CLI script that uses the new client function.
3.  **Pattern**: Always allow the user to specify a `group_name` rather than a `group_id` for better UX. Use `find_group_by_name()` for this.

---

## 🔧 Technical Constraints
*   **Environment**: Windows (PowerShell) is the primary OS. Use `$env:PYTHONPATH="."` for all script executions.
*   **NiFi Version**: Compatible with NiFi 1.x and 2.x REST APIs.
*   **Configuration**: All secrets MUST go in `env/.env`, never hardcode them.

---

## 🕵️ Troubleshooting for AI
*   **Connection Refused**: Check if NiFi is running on the URL specified in `settings.nifi_url`.
*   **Invalid Revision**: Ensure `_get_revision()` is called immediately before an update.
*   **JSON Parse Error**: The shell often escapes quotes differently (e.g., `\"` vs `"`). The `parse_curl` function in `flow_generator.py` uses `shlex` to handle this.
