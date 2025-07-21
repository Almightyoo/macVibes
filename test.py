from pynput import keyboard

def on_press(key):
    print(key)


def on_press(key):
    try:
        keyname = key.char.lower() if hasattr(key, 'char') and key.char else key.name.lower()
        print(keyname)
    except Exception as e:
        print(f"Error handling key press: {e}")


listener = keyboard.Listener(on_press=on_press)
listener.start()
listener.join()
