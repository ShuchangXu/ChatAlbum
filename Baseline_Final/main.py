import os
import time
import keyboard
from voice_interface import Recorder, Polly
from baseline_final import BaselineFinal
from dotenv import load_dotenv

user = "hjs_1"
resume = None#"zhy_2_20240222_2.log"

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
    
    baseline = BaselineFinal(api_key, user, resume)

    if not resume:
        reply = baseline.introduction()
        agent_reply(reply)
    else:
        agent_reply(baseline.chat_history[-1]["content"])

    while True:
        try:
            user_input = get_input()
            if user_input.replace(" ", "") == "quit":
                baseline.save_chat_history()
                break
            
            reply = baseline.chat(user_input)
            agent_reply(reply)
        except Exception as e:
            print(e)
            baseline.save_chat_history()
            break