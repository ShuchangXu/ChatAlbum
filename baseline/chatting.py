import os
from ChatBots import BaselineChatBot
from dotenv import load_dotenv


MAX_TOKENS = 200
MODEL = "gpt-4-vision-preview"



if __name__=="__main__":
    load_dotenv()
    api_key=os.getenv("OPENAI_API_KEY")
    mChatBot = BaselineChatBot(api_key, MODEL, MAX_TOKENS, user="dev")

    print("在每轮对话中，请您: (1) 输入对话内容并以换行键结尾；或，(2) 输入 'quit' 退出")
    continuing = True
    while continuing:
        user_input = input("\n用户输入: ")
        if user_input == "quit":
            mChatBot.save_chat_history()
            break    
        continuing = mChatBot.single_round_chat(user_input)