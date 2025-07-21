from key_to_code import key_to_code
from pynput import keyboard
from pynput import mouse
import json
from pydub import AudioSegment
import numpy as np
from collections import deque
import threading
import sounddevice as sd
import time

######################
###     Config     ###
######################

pad = 270                           # Padding around each key sound
fade_in = 10                       # Fade-in time in ms
fade_out = 30                       # Fade-out time in ms
max_concurrent_sounds = 4           # max no of overlapping key sounds
volume_red_per_layer = 0.2          # Volume reduction for each overlapping sound

soundpack = 'cherrymx-black-abs'                      # 'cherrymx-brown-abs' | 'cherrymx-black-abs' | 'tealios-v2_Akira' | 'apex-pro-tkl-v2_Akira'
volume = 2

###########################
###     init config     ###
###########################

with open(f'assets/{soundpack}/config.json', 'r') as f:
    config = json.load(f)
defines = config['defines']
type = config['key_define_type']





class AudioMixer:
    def __init__(self, samplerate):
        self.activeSounds = deque(maxlen = max_concurrent_sounds)
        self.lock = threading.Lock()
        self.stream = sd.OutputStream(
            samplerate = samplerate,
            channels = 2,
            blocksize = 1024,
            callback = self.audio_callback
        )
        self.stream.start()

    def audio_callback(self, outdata, frames, time, status):
        with self.lock:
            outdata.fill(0)
            for i, (samples, pos, volume) in enumerate(list(self.activeSounds)):
                remaining = len(samples) - pos
                if remaining <= 0:
                    continue
                
                available = min(frames, remaining)
                if available > 0:
                    mixed = samples[pos:pos+available] * volume
                    if mixed.shape[0] == outdata.shape[0]:
                        outdata[:] += mixed
                    else:
                        outdata[:mixed.shape[0]] += mixed
                    self.activeSounds[i] = (samples, pos + available, volume)

    def play(self, samples):
        with self.lock:
            volume = 1.0 - (len(self.activeSounds) * volume_red_per_layer)
            volume = max(0.3, volume) 
            self.activeSounds.append((samples, 0, volume))
    
    def cleanup(self):
        with self.lock:
            self.activeSounds = deque(
                (s for s in self.activeSounds if s[1] < len(s[0])),
                maxlen=max_concurrent_sounds
            )

def on_press(key):
    try:
        keyname = key.char.lower() if hasattr(key, 'char') and key.char else key.name.lower()
        code = str(key_to_code.get(keyname))
        if code and code in key_samples:
            samples, _ = key_samples[code]
            mixer.play(samples)
    except Exception as e:
        print(f"Error handling key press: {e}")


def mixer_cleanup():
    while True:
        time.sleep(0.5)
        mixer.cleanup()

if(type == 'single'):
    
    sound = AudioSegment.from_file(f'assets/{soundpack}/sound.ogg', format='ogg')
    key_samples = {}
    for code, (start_ms, duration_ms) in defines.items():
        snippet = sound[start_ms:start_ms + duration_ms + pad]
        snippet = snippet.fade_in(fade_in).fade_out(fade_out)
        samples = np.array(snippet.get_array_of_samples())
        samples = samples.reshape((-1, 2))
        samples = samples.astype(np.float32) / np.iinfo(samples.dtype).max * 0.8
        key_samples[code] = (samples, snippet.frame_rate)

    mixer = AudioMixer(snippet.frame_rate)
    listener = keyboard.Listener(on_press=on_press)
    listener.start()
    cleanup_thread = threading.Thread(target=mixer_cleanup, daemon=True)
    cleanup_thread.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        listener.stop()
        mixer.stream.close()

    
if(type == 'multi'):
    
    key_samples = {}
    for code, path in defines.items():
        sound = AudioSegment.from_file(f'assets/{soundpack}/{path}', format='wav')
        sound = sound.set_channels(2)
        sound = sound.fade_in(fade_in).fade_out(fade_out)
        samples = np.array(sound.get_array_of_samples())
        samples = samples.reshape((-1, 2))
        samples = samples.astype(np.float32) / np.iinfo(samples.dtype).max * 0.8
        samples *= volume
        
        key_samples[code] = (samples, sound.frame_rate)
    
    mixer = AudioMixer(sound.frame_rate)
    listener = keyboard.Listener(on_press=on_press)
    listener.start()
    cleanup_thread = threading.Thread(target=mixer_cleanup, daemon=True)
    cleanup_thread.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        listener.stop()
        mixer.stream.close()

else:
    print('The type must be single or multi')

