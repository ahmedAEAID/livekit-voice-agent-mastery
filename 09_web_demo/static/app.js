// Minimal LiveKit browser client for the voice agent demo.
//
// Responsibilities:
//   1. Fetch a token from the local server and connect to the room.
//   2. Publish the microphone and play the agent's audio.
//   3. Register the `show_confirmation` RPC method so the agent can pop a real
//      confirmation dialog and receive "yes"/"no" back.

const { Room, RoomEvent, Track } = LivekitClient;

const els = {
  connect: document.getElementById("connect"),
  disconnect: document.getElementById("disconnect"),
  status: document.getElementById("status"),
  audio: document.getElementById("audio"),
  modal: document.getElementById("modal"),
  modalMessage: document.getElementById("modal-message"),
  confirmYes: document.getElementById("confirm-yes"),
  confirmNo: document.getElementById("confirm-no"),
};

let room = null;

function setStatus(text) {
  els.status.textContent = text;
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
      resolve(answer);
    };
    const onYes = () => finish("yes");
    const onNo = () => finish("no");
    els.confirmYes.addEventListener("click", onYes);
    els.confirmNo.addEventListener("click", onNo);
  });
}

function attachAgentAudio(track) {
  const element = track.attach();
  element.autoplay = true;
  els.audio.appendChild(element);
}

async function connect() {
  els.connect.disabled = true;
  setStatus("Requesting token…");

  const res = await fetch("/token");
  if (!res.ok) {
    setStatus("Could not get a token. Is the server running with valid .env.local?");
    els.connect.disabled = false;
    return;
  }
  const { url, token } = await res.json();

  room = new Room({ adaptiveStream: true, dynacast: true });

  room.on(RoomEvent.TrackSubscribed, (track) => {
    if (track.kind === Track.Kind.Audio) attachAgentAudio(track);
  });
  room.on(RoomEvent.Disconnected, () => onDisconnected());

  setStatus("Connecting…");
  await room.connect(url, token);

  // The agent calls this method via perform_rpc(method="show_confirmation").
  // Whatever string we return is delivered back to the agent.
  room.localParticipant.registerRpcMethod("show_confirmation", async (data) => {
    return await askConfirmation(data.payload);
  });

  await room.localParticipant.setMicrophoneEnabled(true);

  els.disconnect.hidden = false;
  setStatus("Connected. Start talking — the agent will greet you.");
}

async function disconnect() {
  if (room) await room.disconnect();
}

function onDisconnected() {
  els.disconnect.hidden = true;
  els.connect.disabled = false;
  els.audio.replaceChildren();
  setStatus("Disconnected.");
  room = null;
}

els.connect.addEventListener("click", () => connect().catch((err) => {
  console.error(err);
  setStatus(`Error: ${err.message}`);
  els.connect.disabled = false;
}));
els.disconnect.addEventListener("click", () => disconnect());
