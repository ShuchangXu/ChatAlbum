import os
from reviver_pro import ReviverPro
from dotenv import load_dotenv

def agent_reply(reply):
    print("Agent:"+reply)

def get_input():
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
            reviver.save_chat_history("cw")
            break
        
        reply = reviver.chat(user_input)
        agent_reply(reply)