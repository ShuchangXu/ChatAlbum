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
    content.append({"role": "system", "content": "Please re-organize this paragraph to make it logically clear."})
    content.append({"role": "user", "content": "Reminisce alongside sighted people allows PVI to use natural language to inquire information within a photo collection, recall associated memories, and enrich their understanding of past moments \cite{jung_so_2022,yoo_understanding_2021}. Such natural communications contribute to engaging reminiscence experiences \cite{jung_so_2022}. However, the reliance on sighted assistance limits the frequency and depth of reminiscence. To address this limitation, we focus on designing a chatbot that enables PVI to reminisce with a photo collection via natural-language communication."})

    response = client.chat.completions.create(
                messages = content,
                model="gpt-4-vision-preview",
                max_tokens = 2000
            )

    reply = response.choices[0].message.content

    print(reply)