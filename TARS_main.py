import sounddevice as sd
import numpy as np
import time
import threading
import queue
import random
import ollama
from faster_whisper import WhisperModel
from piper.voice import PiperVoice

# ── Models ────────────────────────────────────────────────────────────────────
stt_model = WhisperModel("small", device="cuda", compute_type="float16")

piper_voice = PiperVoice.load("en_US-ryan-high.onnx")
SAMPLE_RATE = piper_voice.config.sample_rate


# ── Helpers ───────────────────────────────────────────────────────────────────
def strip_think_tags(text: str) -> str:
    if "<think>" in text and "</think>" in text:
        return text.split("</think>", 1)[-1].strip()
    if "<think>" in text:
        return ""
    return text


def piper_speak(text: str):
    """Working TTS using phoneme pipeline + silence padding."""
    all_audio = []
    phonemes = piper_voice.phonemize(text)

    for sentence_phonemes in phonemes:
        phoneme_ids = piper_voice.phonemes_to_ids(sentence_phonemes)
        audio = piper_voice.phoneme_ids_to_audio(phoneme_ids)
        all_audio.append(np.array(audio, dtype=np.float32))

    if not all_audio:
        return

    full_audio = np.concatenate(all_audio)
    padding = np.zeros(int(SAMPLE_RATE * 0.5), dtype=np.float32)
    full_audio = np.concatenate([full_audio, padding]).reshape(-1, 1)

    sd.play(full_audio, samplerate=SAMPLE_RATE, blocking=True)


# ── Main class ────────────────────────────────────────────────────────────────
class TARS_main:
    def __init__(self):
        # ── TTS queue + dedicated thread ──────────────────────────────────────
        self.tts_queue: queue.Queue[str | None] = queue.Queue()
        self.tts_thread = threading.Thread(target=self._tts_worker, daemon=True)
        self.tts_thread.start()

        # ── STT → LLM pipeline queue (max 3 jobs; older audio dropped) ────────
        self.audio_queue: queue.Queue[np.ndarray] = queue.Queue(maxsize=3)
        self.pipeline_thread = threading.Thread(target=self._pipeline_worker, daemon=True)
        self.pipeline_thread.start()

        # ── Audio capture state ───────────────────────────────────────────────
        self.FS            = 16000
        self.THRESHOLD     = 0.2
        self.SILENCE_LIMIT = 0.5
        self.last_speech_time: float | None = None
        self.is_speaking   = False
        self.audio_buffer: list[np.ndarray] = []
        self.is_tars_speaking = False  # ADD THIS
        
        # ── Proactive monitor ─────────────────────────────────────────────────
        self.last_interaction_time = time.time()
        self.proactive_timeout     = 100
        self.proactive_thread = threading.Thread(target=self._proactive_monitor, daemon=True)
        self.proactive_thread.start()

    # ── TTS worker ────────────────────────────────────────────────────────────
    def _tts_worker(self):
        """Dedicated thread: pulls text from queue and speaks it."""
        while True:
            text = self.tts_queue.get()
            if text is None:
                break
            try:
                self.is_tars_speaking = True
                piper_speak(text)
            except Exception as e:
                print(f"[TTS Error]: {e}")
            finally:
                time.sleep(0.1)        # let speaker output fully decay before re-enabling mic
                self.is_tars_speaking = False
                self.tts_queue.task_done()

    def speak(self, text: str):
        """Non-blocking: clean text, print, hand off to TTS thread."""
        text = strip_think_tags(text)
        if not text or text.strip().upper() == "IGNORE":
            return
        print(f"TARS: {text}")
        self.tts_queue.put(text)

    # ── STT → LLM pipeline worker ─────────────────────────────────────────────
    def _pipeline_worker(self):
        while True:
            audio_data = self.audio_queue.get()
            try:
                print("Transcribing...")
                segments, _ = stt_model.transcribe(audio_data, beam_size=1)
                text = "".join(s.text for s in segments).strip()

                if not text or text == "You":
                    continue

                print(f"User: {text}")
                self.last_interaction_time = time.time()

                self._ask_ai_and_speak(text)

            except Exception as e:
                print(f"[Pipeline Error]: {e}")
            finally:
                self.audio_queue.task_done()
                print("Ready...")


    def _ask_ai_and_speak(self, prompt: str):
        system = (
            "You are TARS, an AI assistant. Humor: 99% - Honesty: 95%. "
            "Be concise. Only respond when it genuinely adds value. "
            "If not relevant, reply with only IGNORE."
        )
        
        buffer = ""
        stream = ollama.chat(
            model="deepseek-r1:7b",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            stream=True,  # stream tokens as they arrive
        )

        for chunk in stream:
            token = chunk["message"]["content"]
            buffer += token

            # Speak each complete sentence immediately without waiting for full response
            for delimiter in [".", "!", "?"]:
                if delimiter in buffer:
                    parts = buffer.split(delimiter, 1)
                    sentence = parts[0].strip() + delimiter
                    buffer = parts[1]
                    if sentence and sentence.upper() != "IGNORE":
                        self.speak(sentence)

        # Speak any remaining text
        if buffer.strip() and buffer.strip().upper() != "IGNORE":
            self.speak(buffer.strip())

    # ── Proactive monitor ─────────────────────────────────────────────────────
    def _proactive_monitor(self):
        while True:
            time.sleep(10)
            idle_time = time.time() - self.last_interaction_time
            if idle_time > self.proactive_timeout and random.random() < 0.10:
                if self.audio_queue.empty() and self.tts_queue.empty():
                    prompt = (
                        "Generate a short, snarky TARS-style observation about "
                        "the current silence, or share a random space fact."
                    )
                    response = self._ask_ai(prompt)
                    self.speak(response)
                    self.last_interaction_time = time.time()

    # ── Audio callback ────────────────────────────────────────────────────────
    def audio_callback(self, indata, frames, time_info, status):
        # Ignore all mic input while TARS is speaking
        if self.is_tars_speaking:
            return
        
        volume = np.linalg.norm(indata) / np.sqrt(len(indata))
        current_time = time.time()

        if volume > self.THRESHOLD:
            if not self.is_speaking:
                print("Speech detected...")
                self.is_speaking = True
            self.last_speech_time = current_time
            self.audio_buffer.append(indata.copy())

        elif self.is_speaking:
            self.audio_buffer.append(indata.copy())

            if self.last_speech_time and (current_time - self.last_speech_time) > self.SILENCE_LIMIT:
                print("Silence reached — queuing for processing...")
                full_audio = np.concatenate(self.audio_buffer).flatten()
                self.is_speaking  = False
                self.audio_buffer = []

                try:
                    self.audio_queue.put_nowait(full_audio)
                except queue.Full:
                    print("[Dropped] Pipeline busy — audio discarded.")

    # ── Entry point ───────────────────────────────────────────────────────────
    def start_listening(self):
        with sd.InputStream(
            callback=self.audio_callback,
            samplerate=self.FS,
            channels=1,
            device=1,
        ):
            print("TARS online. Listening...\n")
            while True:
                time.sleep(1)


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    tars = TARS_main()
    tars.start_listening()



    # piper_speak("Hi, welcome to TARS; I'll be your assistant for today. How can I help you?")


    # devices = sd.query_devices()
    # for i, device in enumerate(devices):
    #     print(f"- Device ID {i}: {device['name']}, Input Channels: {device['max_input_channels']}, Output Channels: {device['max_output_channels']}")
