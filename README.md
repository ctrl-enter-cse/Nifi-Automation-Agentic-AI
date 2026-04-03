# NiFi AI Agent: Project Blueprint & "Brain" Documentation

The **NiFi AI Agent** is an automation and orchestration layer designed to simplify the management of Apache NiFi. It bridges the gap between high-level service definitions (like `curl` commands) and the complex, low-level configuration required by NiFi REST APIs.

---

## 🏗️ Project Architecture

The project is structured into three distinct layers:

### 1. The "Management Layer" (`/app`)
This layer handles the core connection to NiFi and provides a web interface for external systems.
*   **`main.py`**: The entry point for the FastAPI application. It exposes endpoints to list, start, and stop processors.
*   **`nifi_client.py`**: **(Core Utility)** This handles the "dirty work" of communicating with NiFi (tokens, revisions, and headers).
*   **`config.py`**: Manages environment-level secrets (NIFI credentials, LLM API keys) using Pydantic.

### 2. The "Brain" Layer (`/scripts`)
This is where the automation logic resides.
*   **`flow_generator.py`**: **The actual brain.** It parses `curl` commands and intelligently decides which NiFi processors are needed to build a working proxy flow.
*   **`config_manager.py`**: Handles "snapshots" of NiFi configurations so you can track changes over time (like a "Git" for NiFi).
*   **`fetch_group.py`**: A discovery engine that can generate a visual Mermaid.js diagram of any flow.

### 3. The "Environment" Layer (`/env`)
*   **`.env`**: Stores the specific connection strings for your local or remote NiFi instance.

---

## 🧠 Why is this function present? (Key Logic Explained)

### 🧩 `parse_curl()` (in `flow_generator.py`)
**Why?** Users often think in terms of "How do I call this API?". By parsing `curl`, we extract the URL, Headers, and Data automatically. This removes the manual burden of configuring every field in `InvokeHTTP`.

### 🔄 `_get_revision()` (in `app/nifi_client.py`)
**Why?** NiFi uses an **optimistic locking system**. You cannot update a processor without sending its current `version` number back to the API. This function ensures your updates never fail due to "Out of Date Revision" errors.

### 🔌 `find_controller_service_by_type()` (in `app/nifi_client.py`)
**Why?** NiFi processors like `HandleHttpRequest` require a "Controller Service" (the Context Map) to function. This function automatically discovers existing services so you don't have to manually paste IDs between scripts.

### 📊 `generate_html()` (in `scripts/fetch_group.py`)
**Why?** NiFi's native UI is powerful but can be overwhelming. This provides a clean, "read-only" visualization that can be shared or embedded without giving full access to the NiFi instance.

---

## 🚀 How to use the "Brain"

To deploy a new flow from an API call, simply run:

```powershell
$env:PYTHONPATH="."
python scripts/flow_generator.py curl -X POST "https://api.example.com/v1/data" -H "Content-Type: json" --data '{"id": 123}'
```

**What the Brain does next:**
1.  **Deconstructs** your curl command into a dictionary.
2.  **Identifies** if a JSON parser (`EvaluateJsonPath`) is needed.
3.  **Spins up** a full NiFi Process Group.
4.  **Wires** the success/failure branches automatically.
5.  **Instantly starts** the flow so you can test it on `localhost:7808`.

---

## 🛠️ Local Setup

Follow these steps to set up the NiFi AI Agent on your local machine:

### 1. Prerequisites
- **Python 3.10+**: Ensure you have Python installed. You can check with `python --version`.
- **Apache NiFi**: A running instance of NiFi (local or remote).
- **Git**: To clone the repository.

### 2. Clone the Repository
```bash
git clone https://github.com/ctrl-enter-cse/Nifi-Automation-Agentic-AI.git
cd Nifi-Automation-Agentic-AI
```

### 3. Install Dependencies
It is recommended to use a virtual environment:
```bash
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the `env/` directory (or use the one in the root if preferred) with the following content:

```env
# AI Provider Setup
LLM_PROVIDER=gemini # or openai

# API Keys
GOOGLE_API_KEY=your_google_api_key
OPENAI_API_KEY=your_openai_api_key

# NiFi Connection Settings
NIFI_URL=https://localhost:8443/nifi-api
NIFI_USERNAME=your_nifi_username
NIFI_PASSWORD=your_nifi_password
```

### 5. Running the Agent
You can start the FastAPI management server:
```bash
$env:PYTHONPATH="."
python app/main.py
```

Or run the flow generator directly from the CLI:
```bash
$env:PYTHONPATH="."
python scripts/flow_generator.py curl -X POST "https://api.example.com/v1/data"
```

---

## 📽️ Execution Example

When you run `python scripts/flow_generator.py <CURL>`:

```text
Terminal: [AI] Analyzing CURL Intent... Identified: PROXY_PASS
Terminal: [Registry] Fetching structures for: InvokeHTTP, HandleHttpRequest, HandleHttpResponse, EvaluateJsonPath, ReplaceText, UpdateAttribute, RouteOnAttribute from the nifi_processor_registry.json
Terminal: [Mapping] Injecting Authorization and Form Fields into Templates...
Terminal: [Wiring] Connecting 4 Processors with 3 Success relationships...
Terminal: [Deployment] Creating Logic_Dummy Workspace... DONE
```

> [!NOTE]
> The generation logic is now driven by `scripts/flow_rules.json`, allowing for rule-based flow construction before the deployment starts.