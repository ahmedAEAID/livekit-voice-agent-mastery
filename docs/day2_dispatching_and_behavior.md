
# 🚀 Day 2: Advanced Dispatching & Agent Behavior

Today's focus was on **Control**: controlling *which* agent enters the room, and controlling *how* that agent behaves and speaks.

---

## 1. Agent Dispatching

Dispatching is the process of assigning a specific agent to a room.

### **A. Automatic Dispatch (Default)**

* **Behavior:** The first available agent automatically joins any new room.
* **Best for:** General use cases where all users get the same assistant.

### **B. Explicit Dispatch (Manual)**

* **Behavior:** The agent **only** joins if specifically requested by its `agent_name`.
* **Prerequisite:** You must set `agent_name="my-agent"` in your `WorkerOptions`.
* **Use Case:**
* **Outbound Calls:** You want a specific agent to call a user.
* **Specialized Agents:** Routing a user to "Sales" vs "Support" based on their button click.



---

## 2. Token-Based Dispatch (Python)

You can force a specific agent to join a room by baking the dispatch rule directly into the **User's Token**. This is powerful for security and personalization.

### **Code Snippet: Creating a Token with Dispatch Rule**

```python
from livekit.api import AccessToken, RoomAgentDispatch, RoomConfiguration, VideoGrants

room_name = "my-room"
agent_name = "test-agent"  # Must match the name in WorkerOptions

def create_token_with_agent_dispatch() -> str:
    token = (
        AccessToken()
        .with_identity("my_participant")
        .with_grants(VideoGrants(room_join=True, room=room_name))
        .with_room_config(
            RoomConfiguration(
                # This list tells LiveKit: "Only let 'test-agent' join this room"
                agents=[
                    RoomAgentDispatch(
                        agent_name="test-agent", 
                        metadata='{"user_id": "12345"}' # Pass custom data to the agent
                    )
                ],
            ),
        )
        .to_jwt()
    )
    return token

```

---

## 3. Prompting Guide

Writing instructions for Voice Agents is different from Text Chatbots.

### **The Pipeline Problem**

* **The Issue:** The LLM (Brain) doesn't know it's part of a voice pipeline (STT -> LLM -> TTS). It thinks it's texting.
* **The Risk:** It might output emojis, markdown lists, or say "As an AI language model...".
* **The Fix:** Explicitly instruct it: *"You are a voice assistant. Speak naturally. Do not use markdown or emojis."*

### **Key Rules for Voice Prompts:**

1. **Conciseness:** Users are impatient. Keep replies short.
2. **No Monologues:** Avoid long paragraphs.
3. **Personality:** Define a clear persona (Friendly, Professional, Funny).

---

## 4. Changing Agents: Handoff vs. Update

How to switch from one agent (e.g., Generalist) to another (e.g., Specialist) during a call.

| Feature | **Agent Handoff** | **Update Agent** |
| --- | --- | --- |
| **Trigger** | **AI-Driven:** The LLM decides based on conversation. | **Code-Driven:** The developer decides based on logic. |
| **Mechanism** | Returns a new Agent class from a `@function_tool`. | Calls `session.update_agent(NewAgent())` directly. |
| **Example** | User asks: "I want to buy", LLM calls `transfer_to_sales`. | Developer sets a timer: "If call > 5 mins, switch agent". |
| **History** | Adds an `AgentHandoff` event to chat history. | Adds an `AgentHandoff` event to chat history. |

---

## 🔜 Next Steps (Tomorrow)

* Deep dive into **Prompting Workflows**.
* Implementing complex **Agent Handoffs** in code.
* Testing **Outbound Calls**.

---

