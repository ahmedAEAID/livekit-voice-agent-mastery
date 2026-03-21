Here is a comprehensive summary of everything we discussed, organized in **Markdown** for your future reference.

---

# 🚀 LiveKit Agent Mastery: Complete Summary

This document summarizes the key concepts, configurations, and troubleshooting steps for building and deploying LiveKit Voice Agents using Python.

---

## 1. Execution Modes: `dev` vs `start`

Understanding how to run your agent is the first step.

| Mode | Command | Purpose | Key Features |
| :--- | :--- | :--- | :--- |
| **Development** | `uv run agent.py dev` | Coding & Debugging | • **Hot Reload:** Restarts automatically.<br>• **Debug Logs:** Detailed WebRTC/API logs.<br>• **Watcher:** Active file monitoring. |
| **Production** | `uv run agent.py start` | Deployment | • **Performance:** Optimized for speed.<br>• **No Reload:** Manual restart required.<br>• **JSON Logs:** For monitoring tools.<br>• **Load Balancing:** Manages CPU/RAM. |

---

## 2. Prewarming (Cold Start vs. Warm Start)

This explains the difference in initialization time (e.g., 8s vs 0.2s).

* **Cold Start (No Prewarming):** The agent loads heavy AI models (VAD, STT, LLM) *after* the user connects.
* *Result:* User hears silence/delay for several seconds.


* **Warm Start (With Prewarming):** The agent loads models into memory when the server starts, *before* any user joins.
* *Result:* Instant response (0.2s).
* *Implementation:* You must define a `prewarm()` function and pass it to `WorkerOptions`.



---

## 3. Worker Options (Configuration Hub)

The `WorkerOptions` class is the correct way to configure your agent in production. It replaces command-line arguments.

### **Code Snippet: Recommended Configuration**

```python
if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            # 1. Functions
            entrypoint_fnc=entrypoint,  # The main agent logic
            prewarm_fnc=prewarm,        # The model loading logic

            # 2. Identity & Networking
            agent_name="my_fast_agent", # Unique name for explicit dispatch
            port=8082,                  # Health check port (Prevents OSError 10048)
            host="0.0.0.0",             # Listen on all interfaces

            # 3. Performance & Load Management
            num_idle_processes=1,       # Reduce to 1 to save CPU on local dev
            load_threshold=0.90,        # Allow up to 90% CPU usage before marking unavailable
            
            # 4. Observability
            prometheus_port=9001,       # Port for raw metrics
        )
    )

```

---

## 4. Networking & Ports

### **Health Check Port (`http_server_port`)**

* **Default:** 8081.
* **Error:** `OSError: [Errno 10048]` means the port is already in use (e.g., running two agents simultaneously).
* **Fix:** Assign a unique `port` in `WorkerOptions` for each agent script (e.g., 8081 for Agent A, 8082 for Agent B).
* **Validation:** Open `http://localhost:8081` in a browser. It returns `OK` if the agent is healthy.

### **Prometheus Port (`prometheus_port`)**

* **Purpose:** Exposes raw metrics for monitoring tools (Grafana).
* **Access:** Open `http://127.0.0.1:9001/metrics`.
* **Data:** Shows CPU load (`lk_agents_worker_load`), active jobs, and Python GC stats.

---

## 5. Dispatching (Routing)

How LiveKit decides which agent handles a room.

* **Automatic Dispatch:** (Default) Any available agent joins any room.
* **Explicit Dispatch:** Enabled by setting `agent_name`. The agent only joins if specifically requested.
* *Use Case:* Separating "Sales Agent" from "Support Agent".
* *Testing:* In the Playground, select the specific agent name from the dropdown.



---

## 6. Observability & Tracing

How to see what your agent is thinking and doing.

### **1. Real-time Analytics (Session Analytics)**

* **Where:** LiveKit Cloud Dashboard -> Sessions -> (Click Active Session) -> **Session Analytics**.
* **What:** Visual timeline of events (User joined, Track published) and latency.
* **When:** Available immediately while the call is active.

### **2. Agent Insights (Deep Tracing)**

* **Where:** LiveKit Cloud Dashboard -> Sessions -> (Click Ended Session) -> **Agent Insights**.
* **What:** Full transcripts, LLM reasoning time, STT delay, and detailed traces.
* **Requirements:**
* Python SDK > v1.3.0 (Check with `uv tree`).
* Feature enabled in Project Settings.



---

## 7. Load Management Logs

Understanding the logs in `start` mode:

* **Log:** `"worker is at full capacity, marking as unavailable"`
* **Meaning:** Your CPU/RAM usage exceeded the `load_threshold`. The agent stops accepting new calls to prevent crashing.


* **Log:** `"worker is below capacity, marking as available"`
* **Meaning:** Resource usage dropped, and the agent is ready again.


* **Fix for Local Dev:** Increase `load_threshold` to `0.95` and set `num_idle_processes` to `1` in `WorkerOptions`.

---

## 8. CLI Commands Cheat Sheet

| Action | Command |
| --- | --- |
| **Download Models** | `uv run agent.py download-files` |
| **Run Dev Mode** | `uv run agent.py dev` |
| **Run Prod Mode** | `uv run agent.py start` |
| **Check Dependencies** | `uv tree` |
| **Create Token** | `lk token create --join --room my-room --participant user1` |