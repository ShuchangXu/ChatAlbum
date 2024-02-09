import os
from ChatBots_Reviver import BaselineChatBot
from dotenv import load_dotenv


MAX_TOKENS = 200
MODEL = "gpt-4-vision-preview"



if __name__=="__main__":
    load_dotenv()
    api_key=os.getenv("OPENAI_API_KEY")
    mChatBot = BaselineChatBot(api_key, MODEL, MAX_TOKENS, user="dev3")

    print("在每轮对话中，请您: (1) 输入对话内容并以换行键结尾；或，(2) 输入 'quit' 退出")
    continuing = True
    while continuing:
        user_input = input("\n用户输入: ")
        if user_input == "quit":
            mChatBot.save_chat_history()
            break    
        continuing = mChatBot.single_round_chat(user_input+"请按如下格式输出结果(不要输出//后的内容):\nA//此次讨论的事件编号\nY or N//这是不是第一次具体讨论这个事件\n你的回答//给用户的正式回复，回答请使用口语，切记不要出现事件编号，照片编号\n要求: 你每次的回复中，要提供新的信息!!! 尽量不要重复之前说过的信息，也不要重复用户说的话。如无必要，不要问用户问题。")