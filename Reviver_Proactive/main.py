import os
import time
import keyboard
from voice_interface import Recorder, Polly
from reviver_pro import ReviverPro
from dotenv import load_dotenv


USE_VUI = False
recorder = Recorder()
polly = Polly()


def agent_reply(reply):
    print("Agent:"+reply)
    if USE_VUI:
        try:
            # Text-to-speech
            polly.synthesize(reply)
        except Exception as e:
            print(e)
        

def get_input():
    if USE_VUI:
        print("请单击【空格键】开始说话:")
        while True:
            if keyboard.is_pressed('space'):
                print("--检测到您按下了空格键--")
                return recorder.start_recording()
    else:
        user_input = input("\nUser:")
        return user_input


if __name__=="__main__":
    load_dotenv()
    api_key=os.getenv("OPENAI_API_KEY")
    reviver = ReviverPro(api_key)

    reviver.init_mtree()

    reply = reviver.introduction()
    agent_reply(reply)
    user_input = get_input()

    reply = reviver.first_event_intro(user_input)
    agent_reply(reply)

    while True:
        user_input = get_input()
        if user_input == "quit":
            reviver.save_chat_history("dev0214")
            break
        
        reply = reviver.chat(user_input)
        agent_reply(reply)