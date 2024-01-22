import os
import time
import json
from ChatBots import BaselineChatBot
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI



MAX_TOKENS = 200
MODEL = "gpt-4-vision-preview"

load_dotenv()
api_key=os.getenv("OPENAI_API_KEY")
mChatBot = BaselineChatBot(api_key, MODEL, MAX_TOKENS, user="dev")

print("在每轮对话中，请您: (1) 输入对话内容并以换行键结尾；或，(2) 输入 'quit' 退出")
while True:
    user_input = input("\n用户输入: ")
    if user_input == "quit":
        mChatBot.save_chat_history()
        break    
    mChatBot.single_round_chat(user_input)