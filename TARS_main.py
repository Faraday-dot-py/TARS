import sounddevice as sd
import numpy as np
import time
import threading
import ollama
import pyttsx3
from faster_whisper import WhisperModel

import random

# variables with system prompts from files in directory


stt_model = WhisperModel("small", device="cuda", compute_type="float32")

class TARS_main:
    def __init__(self):
        # Keyboard listener
        # self.kb_thread = threading.Thread(target=self.keyboard_listener, daemon=True)
        # self.kb_thread.start()

        # Audio processing parameters
        self.FS = 16000
        self.THRESHOLD = 0.1
        self.SILENCE_LIMIT = 1.0
        self.last_speech_time = None
        self.is_speaking = False
        self.is_busy = False
        self.audio_buffer = []
        
        # --- Queue Tracking Variables ---
        self.task_counter = 0      # Current index (x)
        self.total_submitted = 0   # Total count (y)
        self.counter_lock = threading.Lock()

        # --- Boredom Monitor ---
        self.last_interaction_time = time.time()
        self.proactive_timeout = 30  # Seconds of silence before TARS speaks
        # self.proactive_thread = threading.Thread(target=self.proactive_monitor, daemon=True)
        # self.proactive_thread.start()
        

    # type to TARS logic (optional, can replace voice)
    # def keyboard_listener(self):
    #     """Non-blocking terminal input loop."""
    #     while True:
    #         # This blocks ONLY this thread, not the whole program
    #         user_text = input("TARS (Type/Speak): ") 
    #         if user_text.strip():
    #             print(f"[Typed]: {user_text}")
    #             # Manually trigger the response logic
    #             self.process_text_input(user_text)

    # def process_text_input(self, text):
    #     """Shared logic for both voice-transcribed and typed text."""
    #     with self.counter_lock:
    #         self.task_counter += 1
    #         idx = self.task_counter
        
    #     # Run AI response in a separate thread so you can keep typing/talking
    #     threading.Thread(target=self._generate_and_speak, args=(text, idx)).start()

    # def _generate_and_speak(self, text, idx):
    #     response = self.ask_ai(text, idx)
    #     self.speak(response)






    # def proactive_monitor(self):
    #     """Checks if TARS should start a conversation spontaneously."""
    #     while True:
    #         time.sleep(10)  # Check every 10 seconds
    #         idle_time = time.time() - self.last_interaction_time
            
    #         # Example: If idle for 5 minutes, 10% chance to speak
    #         # if idle time met, start a roll every 5 seconds, if roll is successful, trigger a proactive conversation
    #         if idle_time > 100 and random.random() < 0.10:
    #             self.initiate_conversation()

    # def initiate_conversation(self):
    #     if not self.is_busy:
    #         prompt = "Generate a short, snarky TARS-style observation about the current silence or a random space fact."
    #         # Use your existing ask_ai and speak logic
    #         response = self.ask_ai(prompt, "AUTONOMOUS")
    #         self.speak(response)
    #         self.last_interaction_time = time.time()


    def speak(self, text):
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
        engine.stop()
        del engine

    def ask_ai(self, prompt, current_idx):
        # Print the thinking status using the passed index and total
        print(f"thinking [{current_idx}-{self.total_submitted}]")
        
        system = "You are TARS, an AI assistant... Humor: 99% - Honesty: 95% :::"
        response = ollama.chat(model="deepseek-r1:7b", messages=[
            {"role": "user", "content": system + "Prompt: " + prompt}
        ])
        return response["message"]["content"]


    def check_if_needed(self, gatekeeper_prompt):
        # This is a lightweight check  to determine if TARS should respond, preventing over-talkativeness.
        print("Checking if TARS should respond...\n")
        response = ollama.chat(model="deepseek-r1:7b", messages=[
            {"role": "user", "content": gatekeeper_prompt}
        ])
        return response["message"]["content"]


    def process_audio_queue(self, audio_data):
        print("Processing audio in background thread...\n\n")
        
        # Increment the index of the task currently starting
        with self.counter_lock:
            self.task_counter += 1
            current_idx = self.task_counter

        def _run_tts():
            print("Transcribing audio...\n")
            try:
                segments, _ = stt_model.transcribe(audio_data)
                text = "".join([s.text for s in segments]).strip()
                print(f"User: {text}")
                if text and text != 'you':
                    # Gatekeeper Logic: Ask AI if it SHOULD respond
                    # This prevents TARS from talking over every single sentence.
                    gatekeeper_prompt = (
                        # f"You are monitoring a conversation. This is what is being discussed: '{text}'. "
                        # "Should TARS intervene? Respond with ONLY 'YES' or 'NO'."
                        
                        "You are a gatekeeper for TARS, an AI assistant."
                        "TARS responds when spoken to directly, or when the content is relevant to TARS." 
                        "TARS does not respond to every single sentence, only when it adds value to the conversation."
                        f"TARS is monitoring a conversation, and this is what is being discussed: --{text}--." 
                        "Should TARS speak? Respond with ONLY 'YES' or 'NO'."
                        "Explain your reasoning briefly in parentheses after your answer."
                    )
                    
                    # Use a lightweight check or a specific instruction in your system prompt
                    should_respond = self.check_if_needed(gatekeeper_prompt) 
                    print(f"Gatekeeper response: {should_respond}")

                    if "YES" in should_respond:
                        response = self.ask_ai(text, current_idx)
                        self.speak(response)


            except Exception as e:
                print(f"Error: {e}")
            finally:
                print("\nReady for next command...")
                self.is_busy = False
        
        threading.Thread(target=_run_tts).start()
        
        

    def audio_callback(self, indata, frames, time_info, status):
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

            if current_time - self.last_speech_time > self.SILENCE_LIMIT:
                print("Silence Limit reached. Sending to LLM...")
                
                # --- NEW: Increment the total count submitted ---
                with self.counter_lock:
                    self.total_submitted += 1
                
                full_audio = np.concatenate(self.audio_buffer).flatten()
                self.is_speaking = False
                self.audio_buffer = []
                threading.Thread(target=self.process_audio_queue, args=(full_audio,)).start()

    def start_listening(self):
        with sd.InputStream(callback=self.audio_callback, samplerate=self.FS, channels=1, device=1):
            print("TARS starting thread. Listening for input...\n")
            while True:
                time.sleep(10)

if __name__ == "__main__":
    awareness_system = TARS_main()
    # awareness_system.speak("Hello, I'm TARS. I'm here to assist you. Let's get started!")
    awareness_system.start_listening()
