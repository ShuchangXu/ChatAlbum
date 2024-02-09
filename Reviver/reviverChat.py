import os
from Reviver import Reviver
from dotenv import load_dotenv

if __name__=="__main__":
    load_dotenv()
    api_key=os.getenv("OPENAI_API_KEY")
    reviver = Reviver(api_key)

    reviver.init_mtree()

    reply = reviver.onboarding()
    print("Agent:"+reply)

    while True:
        user_input = input("\nUser:")
        if user_input == "quit":
            reviver.save_chat_history("cw")
            break
        
        reply = reviver.chat(user_input)
        print("Agent:"+reply)