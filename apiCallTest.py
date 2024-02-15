import os
from dotenv import load_dotenv
from openai import OpenAI

TIME_OUT = 30

if __name__=="__main__":
    load_dotenv()
    api_key=os.getenv("OPENAI_API_KEY")
    print(api_key)
    
    client = OpenAI(api_key=api_key, timeout=TIME_OUT)
    content = []
    content.append({"role": "system", "content": "You are an assistant that helps the user do research. Please respond within 200 characters."})
    content.append({"role": "user", "content": "What are proactive conversational agents?"})

    response = client.chat.completions.create(
                messages = content,
                model="gpt-4-vision-preview",
                max_tokens = 200
            )

    reply = response.choices[0].message.content

    print(reply)