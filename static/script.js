let isRecording = false;
let audioSocket;
let controlSocket;
let microphone;

function initializeSockets() {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsBase = `${wsProtocol}//${window.location.host}`;

    audioSocket = new WebSocket(`${wsBase}/ws`);
    controlSocket = new WebSocket(`${wsBase}/control`);

    audioSocket.onopen = () => console.log("Audio WebSocket connected");
    controlSocket.onopen = () => console.log("Control WebSocket connected");
    
    audioSocket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        console.log(data)
        document.getElementById("captions").innerHTML = data.transcription;
    };

    audioSocket.onerror = (error) => console.error("Audio WebSocket error:", error);
    controlSocket.onerror = (error) => console.error("Control WebSocket error:", error);

    audioSocket.onclose = () => console.log("Audio WebSocket closed");
    controlSocket.onclose = () => console.log("Control WebSocket closed");
}

async function getMicrophone() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        return new MediaRecorder(stream, { mimeType: "audio/webm" });
    } catch (error) {
        console.error("Error accessing microphone:", error);
        throw error;
    }
}

async function openMicrophone(microphone) {
    return new Promise((resolve) => {
        microphone.onstart = () => {
            console.log("Client: Microphone opened");
            document.body.classList.add("recording");
            resolve();
        };
        microphone.ondataavailable = async (event) => {
            if (event.data.size > 0 && audioSocket.readyState === WebSocket.OPEN) {
                audioSocket.send(event.data);
            }
        };
        microphone.start(1000);
    });
}

async function startRecording() {
    isRecording = true;
    microphone = await getMicrophone();
    console.log("Client: Waiting to open microphone");
    await openMicrophone(microphone);
    controlSocket.send(JSON.stringify({ action: "start" }));
}

async function stopRecording() {
    if (isRecording) {
        microphone.stop();
        microphone.stream.getTracks().forEach((track) => track.stop());
        controlSocket.send(JSON.stringify({ action: "stop" }));
        microphone = null;
        isRecording = false;
        console.log("Client: Microphone closed");
        document.body.classList.remove("recording");
    }
}

document.addEventListener("DOMContentLoaded", () => {
    initializeSockets();

    const recordButton = document.getElementById("record");

    recordButton.addEventListener("click", () => {
        if (!isRecording) {
            startRecording().catch((error) =>
                console.error("Error starting recording:", error)
            );
        } else {
            stopRecording().catch((error) =>
                console.error("Error stopping recording:", error)
            );
        }
    });
});