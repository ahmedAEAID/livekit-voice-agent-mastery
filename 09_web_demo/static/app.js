// Minimal LiveKit browser client for the voice agent demo.
//
// It shows RPC in both directions:
//   - agent -> frontend: the agent calls `show_confirmation`, we pop a modal.
//   - frontend -> agent: we call `agent.state` to create a note on the agent.

const { Room, RoomEvent, Track, ParticipantKind } = LivekitClient;

const els = {
  connect: document.getElementById("connect"),
  disconnect: document.getElementById("disconnect"),
  statusPill: document.getElementById("status-pill"),
  audio: document.getElementById("audio"),
  log: document.getElementById("log"),
  rpcPanel: document.getElementById("rpc-panel"),
  noteTitle: document.getElementById("note-title"),
  noteContent: document.getElementById("note-content"),
  sendRpc: document.getElementById("send-rpc"),
  modal: document.getElementById("modal"),
  modalMessage: document.getElementById("modal-message"),
  confirmYes: document.getElementById("confirm-yes"),
  confirmNo: document.getElementById("confirm-no"),
};

let room = null;
let agentIdentity = null;

const PILL_CLASS = {
  idle: "pill pill-idle",
  busy: "pill pill-busy",
  live: "pill pill-live",
  error: "pill pill-error",
};

function setStatus(text, state = "idle") {
  els.statusPill.textContent = text;
  els.statusPill.className = PILL_CLASS[state] || PILL_CLASS.idle;
}

function log(text, kind = "info") {
  const li = document.createElement("li");
  li.className = `log-item log-${kind}`;
  const time = new Date().toLocaleTimeString();
  li.innerHTML = `<span class="log-time">${time}</span><span>${text}</span>`;
  els.log.prepend(li);
}

// Browsers only expose the microphone on a secure context: https, or http on
// localhost / 127.0.0.1. Opening 0.0.0.0:8080 silently disables it.
function microphoneAvailable() {
  return Boolean(navigator.mediaDevices && navigator.mediaDevices.getUserMedia);
}

// Show the modal and resolve with "yes" or "no" when the user clicks.
function askConfirmation(message) {
  els.modalMessage.textContent = message;
  els.modal.hidden = false;

  return new Promise((resolve) => {
    const finish = (answer) => {
      els.modal.hidden = true;
      els.confirmYes.removeEventListener("click", onYes);
      els.confirmNo.removeEventListener("click", onNo);
      log(`You answered "${answer}" to the agent.`, "rpc");
      resolve(answer);
    };
    const onYes = () => finish("yes");
    const onNo = () => finish("no");
    els.confirmYes.addEventListener("click", onYes);
    els.confirmNo.addEventListener("click", onNo);
  });
}

function rememberAgent(participant) {
  if (participant.kind === ParticipantKind.AGENT && !agentIdentity) {
    agentIdentity = participant.identity;
    log(`Agent joined: ${participant.identity}`, "ok");
    setStatus("Agent connected", "live");
  }
}

async function connect() {
  if (!microphoneAvailable()) {
    setStatus("Microphone blocked", "error");
    log(
      "Microphone is unavailable. Open the page at http://localhost:8080 " +
        "(not 0.0.0.0) so the browser allows the mic.",
      "error",
    );
    return;
  }

  els.connect.disabled = true;
  setStatus("Requesting token…", "busy");

  let url, token;
  try {
    const res = await fetch("/token");
    if (!res.ok) throw new Error(`token request failed (${res.status})`);
    ({ url, token } = await res.json());
  } catch (err) {
    setStatus("Token error", "error");
    log(`Could not get a token: ${err.message}. Is .env.local valid?`, "error");
    els.connect.disabled = false;
    return;
  }

  room = new Room({ adaptiveStream: true, dynacast: true });

  room.on(RoomEvent.TrackSubscribed, (track) => {
    if (track.kind === Track.Kind.Audio) {
      const element = track.attach();
      element.autoplay = true;
      els.audio.appendChild(element);
      log("Agent audio stream connected.", "ok");
    }
  });
  room.on(RoomEvent.ParticipantConnected, rememberAgent);
  room.on(RoomEvent.Disconnected, onDisconnected);

  setStatus("Connecting…", "busy");
  await room.connect(url, token);
  log("Connected to the LiveKit room.", "ok");

  // The agent calls this method via perform_rpc(method="show_confirmation").
  room.localParticipant.registerRpcMethod("show_confirmation", async (data) => {
    log(`Agent asked: "${data.payload}"`, "rpc");
    return await askConfirmation(data.payload);
  });

  await room.localParticipant.setMicrophoneEnabled(true);
  log("Microphone is live — start talking.", "ok");

  // The agent may already be in the room when we connect.
  room.remoteParticipants.forEach(rememberAgent);

  els.disconnect.hidden = false;
  els.rpcPanel.hidden = false;
  setStatus("Connected", "live");
}

async function sendStateRpc() {
  if (!room) return;
  if (!agentIdentity) {
    log("No agent in the room yet — start the RPC agent first.", "error");
    return;
  }

  const payload = JSON.stringify({
    operation: "create",
    object_type: "note",
    data: {
      title: els.noteTitle.value || "Untitled",
      content: els.noteContent.value || "",
    },
  });

  els.sendRpc.disabled = true;
  log(`Calling agent.state → create note "${els.noteTitle.value}"…`, "rpc");
  try {
    const response = await room.localParticipant.performRpc({
      destinationIdentity: agentIdentity,
      method: "agent.state",
      payload,
      responseTimeout: 10000,
    });
    const parsed = JSON.parse(response);
    log(`Agent replied: ${parsed.message || response}`, "ok");
  } catch (err) {
    log(`RPC to agent failed: ${err.message}`, "error");
  } finally {
    els.sendRpc.disabled = false;
  }
}

async function disconnect() {
  if (room) await room.disconnect();
}

function onDisconnected() {
  els.disconnect.hidden = true;
  els.rpcPanel.hidden = true;
  els.connect.disabled = false;
  els.audio.replaceChildren();
  agentIdentity = null;
  room = null;
  setStatus("Not connected", "idle");
  log("Disconnected.", "info");
}

els.connect.addEventListener("click", () =>
  connect().catch((err) => {
    console.error(err);
    setStatus("Error", "error");
    log(`Error: ${err.message}`, "error");
    els.connect.disabled = false;
  }),
);
els.disconnect.addEventListener("click", () => disconnect());
els.sendRpc.addEventListener("click", () => sendStateRpc());
