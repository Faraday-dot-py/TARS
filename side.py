import sounddevice as sd
import numpy as np
import time
import queue
import threading

import pyttsx3

from faster_whisper import WhisperModel

stt_model = WhisperModel("small", device="cuda", compute_type="float16")

class Side1:
    def __init__(self):
        self.FS = 16000
        self.THRESHOLD = 0.05  # Adjust based on background noise
        self.SILENCE_LIMIT = 1.0 # 1 second trigger
        self.last_speech_time = None
        self.is_speaking = False


        # Temporary storage for audio blocks
        self.audio_buffer = []


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
            # User was speaking but is now silent, keep buffering silence briefly
            self.audio_buffer.append(indata.copy())
            # print("Silence detected, waiting for 1s to confirm end of speech...")
            
            # Check if silence has lasted 1 second
            if current_time - self.last_speech_time > self.SILENCE_LIMIT:
                print("1s Silence detected. Sending to LLM...")
                # Process the buffered audio (this would be replaced with actual processing)
                full_audio = np.concatenate(self.audio_buffer).flatten()
                self.is_speaking = False
                self.audio_buffer =[]  # Clear buffer for next command
                
                threading.Thread(target=self.process_audio_queue, args=(full_audio,)).start()


    def process_audio_queue(self, audio_data):
        def _run_tts():    
            try:
                # Transcribe
                segments, _ = stt_model.transcribe(audio_data)
                text = "".join([s.text for s in segments]).strip()
                
                if text:
                    print(f"User: {text}")
                    # Get LLM response
                    # response = self.ask_ai(text)
                    # Text to Speech (this is blocking, which is good here)
                    self.speak(text)

            except Exception as e:
                print(f"Error: {e}")

            finally:
                # UNLOCK: Re-open the microphone for the next command
                print("\nReady for next command...")
                self.is_busy=False

        # Run in a separate thread if not already in one
        threading.Thread(target=_run_tts).start()

    def start_listening(self):

        with sd.InputStream(callback=self.audio_callback, samplerate=self.FS, channels=1, device=1):
            print("Listening constantly... (Press Ctrl+C to stop)")
            while True:
                time.sleep(10) # Keeps main thread alive


    def speak(self, text):

        # Initializing inside the function ensures a fresh state every time
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()
        # Explicitly stop and delete the engine to prevent loop hanging
        engine.stop()
        del engine 

    print("Assistant: Hello! Type 'quit' to end the chat.")

    # # 2. Start the conversation loop
    # while True:
    #     # Get your input
    #     user_input = input("You: ")

    #     # Check if you want to stop
    #     if user_input.lower() in ["quit", "exit", "bye"]:
    #         speak("Goodbye!")
    #         break

    #     # 3. They talk back
    #     # You can put logic here to change what they say based on your input
    #     response = f"You said {user_input}" 
        
    #     print(f"Assistant: {response}")
    #     # speak(response)
    #     start_listening()


if __name__ == "__main__":
    awareness_system = Side1()

    # run the audio system (STT + TTS)
    # while True:
    #     awareness_system.record_and_transcribe()

    while True:
        awareness_system.start_listening()

