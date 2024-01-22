import os
import time
# from dotenv import load_dotenv
from openai import OpenAI

MAX_TOKEN = 100
MODEL = "gpt-4-vision-preview"

# load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"), timeout=600)
with open('./prompts/system_guide.txt', 'r', encoding='utf-8') as f:
    system_guide = f.read()    
with open('./photos/photo_description.txt', 'r', encoding='utf-8') as f:
    photo_description = f.read()
    
    
    
content = [
    {"role": "system", "content": system_guide},
    {"role": "user", "content": photo_description},
]
time_cost = []

print("在每轮对话中，请您：（1）输入对话内容并以换行键结尾；或，（2）输入 'quit' 退出")

# start = time.time()
# try:
while True:
    user_input = input("用户输入：")
    if user_input == "quit":
        break    
    content.append({
        "role": "user", "content": user_input
    })
    
    start_time = time.time()
    # start = start_time
    response = client.chat.completions.create(
            model = MODEL,
            max_tokens = MAX_TOKEN,
            messages = content
            )
    end_time = time.time()
    
    print(response.choices[0].message)
    time_cost.append({
        "duration_ms": int((end_time - start_time) * 1000),
        "input_token": response.usage.prompt_tokens,
        "output_token": response.usage.completion_tokens
    })
    
print(MODEL)
print(time_cost)
    
# except Exception as e:
#     end = time.time()
#     print(e)
#     print(end - start, 's')