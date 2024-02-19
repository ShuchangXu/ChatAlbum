import os
import time
import keyboard
from voice_interface import Recorder, Polly
from reviver_pro_v2 import ReviverPro
from dotenv import load_dotenv


USE_VUI = True
recorder = Recorder()
polly = Polly()


def agent_reply(reply):
    print("\nAgent:"+reply)
    if USE_VUI:
        try:
            # Text-to-speech
            polly.synthesize(reply)
        except Exception as e:
            print(e)
        

def get_input():
    if False:
        print("\n请单击【空格键】开始说话:")
        while True:
            if keyboard.is_pressed('space'):
                print("--检测到您按下了空格键--")
                user_input = recorder.start_recording()
                print("User:"+user_input)
                return user_input
    else:
        user_input = input("\nUser:")
        return user_input


if __name__=="__main__":
    load_dotenv()
    api_key=os.getenv("GPT_API_KEY")
    
    user = "dev_wmq"
    resume = None
    reviver = ReviverPro(api_key, user, resume)

    if not resume:
        reply = reviver.introduction()
        agent_reply(reply)
    else:
        agent_reply(reviver.chat_history[-1]["content"])

    while True:
        try:
            user_input = get_input()
            if user_input.replace(" ", "") == "quit":
                reviver.save_chat_history()
                break
            
            reply = reviver.chat(user_input)
            agent_reply(reply)
        except Exception as e:
            print(e)
            reviver.save_chat_history()
            break