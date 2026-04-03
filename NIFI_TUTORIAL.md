# 🚀 Apache NiFi Tutorial & Best Practices

This document serves as a comprehensive guide for working with Apache NiFi, covering architecture, practical rules, and step-by-step usage.

---

## ✅ 1. SHORT SUMMARY (Quick Understanding)

**Apache NiFi** is a **real-time data ingestion and flow automation tool** used to move, transform, and manage data between systems.

### Key Points:
*   **Drag-and-drop UI** for building data pipelines
*   Uses **FlowFiles** (data + metadata)
*   Built using **Processors** connected into flows
*   Supports protocols like HTTP, SFTP, Kafka, etc.
*   Provides **data lineage (provenance)** for tracking
*   Highly configurable, secure, and scalable

> **NiFi = Data pipeline builder + ETL tool + real-time flow manager**

---

## 📘 2. DETAILED EXPLANATION

### 🔹 Core Architecture

#### 1. FlowFile
The basic unit of data in NiFi. It contains:
*   **Content:** The actual data.
*   **Attributes:** Metadata like filename, UUID, etc.

#### 2. Processor
The core building blocks that perform operations:
*   **Fetch data:** `GetFile`, `GetHTTP`
*   **Transform:** `ReplaceText`, `JoltTransformJSON`
*   **Send data:** `PutFile`, `PutKafka`

#### 3. Flow
A pipeline created by connecting processors.
Example: `GetFile` → `ReplaceText` → `PutFile`

#### 4. Process Group
Logical grouping of flows to help organize large projects.

#### 5. Queues
Hold FlowFiles between processors, helping with:
*   **Backpressure management**
*   **Load Balancing**

#### 6. Repositories
| Repository | Purpose |
| :--- | :--- |
| **FlowFile Repo** | Stores metadata (attributes) |
| **Content Repo** | Stores the actual data |
| **Provenance Repo** | Tracks event history for every FlowFile |

#### 7. Data Provenance
Tracks every step of the data, which is essential for debugging and auditing.

---

### 🔹 Processor Categories
| Category | Example |
| :--- | :--- |
| Ingestion | `GetFile`, `GetHTTP` |
| Routing | `RouteOnAttribute` |
| Transformation | `ReplaceText` |
| Database | `ExecuteSQL` |
| Output | `PutFile`, `PutKafka` |
| HTTP | `InvokeHTTP` |

---

### 🔹 UI & API
*   **Drag & drop canvas** for visual orchestration.
*   **Real-time monitoring** and error tracking via **Bulletins**.
*   **REST API Support:** NiFi exposes endpoints like `/nifi-api/processors`, `/nifi-api/flow`, etc.

---

## ⚙️ 3. NIFI RULES (PRACTICAL BEST PRACTICES)

### 🔸 Flow Design Rules
1.  **Always define success & failure paths:** Never leave failure unhandled.
2.  **Use clear naming:** e.g., `GetFile_Input_CustomerData`.
3.  **Use Process Groups:** Separate flows by API, Module, or Project.

### 🔸 Performance Rules
4.  **Use backpressure:** Avoid memory overflow by limiting queue sizes.
5.  **Set concurrent tasks properly:** Don’t overload the system resources.
6.  **Use batching:** Process records in batches where possible for efficiency.

### 🔸 Error Handling Rules
7.  **Always route failures:** Ensure every failure path is logged or handled.
8.  **Use retry mechanisms:** Implement retry loops (e.g., failure → retry queue → processor).

### 🔸 Security & Configuration
9.  **Use HTTPS/SSL:** Always secure communication.
10. **Zero Hardcoding:** Never hardcode passwords or tokens; use Parameter Contexts.
11. **Parameter Contexts:** Use these for environment-specific configurations.
12. **Templates:** Store and reuse templates for common patterns.

---

## 🚀 4. HOW TO USE NIFI (STEP-BY-STEP)

### Basic Flow Example: Read file → Modify → Store
1.  **Step 1:** Add `GetFile` (Set input directory to `/input`).
2.  **Step 2:** Add `ReplaceText` (Configure content transformation).
3.  **Step 3:** Add `PutFile` (Set output directory to `/output`).
4.  **Step 4:** **Connect processors:** Link them on the canvas.
5.  **Step 5:** **Configure relationships:** Set `success` to the next step and handle `failure`.
6.  **Step 6:** **Start processors:** Enable the flow.

---

## 🧠 FINAL UNDERSTANDING
Think of NiFi as your **Pipeline Builder**, **Data Router**, **Transformation Engine**, and **Monitoring Tool**.

---

## 🔥 Enterprise Level (Banking / DMS)
For advanced use-cases like banking APIs or Document Management Systems (DMS):
*   **Clustering:** Multi-node setup for scalability.
*   **Remote Process Groups:** Cross-instance data sharing.
*   **Custom Processors:** Developed using Java + Maven for unique requirements.
