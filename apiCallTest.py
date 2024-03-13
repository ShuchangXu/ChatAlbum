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
    content.append({"role": "system", "content": "You are an assistant that helps me polish research papers. Please refine my writing."})
    content.append({"role": "user", "content": "To illustrate Memory Reviver, we follow \textit{Robin}, a PVI who hopes to revisit a photo collection for a trip nine years ago. It happened so long ago that he hardly remembers anything about it. "})

    response = client.chat.completions.create(
                messages = content,
                model="gpt-4-vision-preview",
                max_tokens = 2000
            )

    reply = response.choices[0].message.content

    print(reply)