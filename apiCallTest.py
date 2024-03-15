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
    content.append({"role": "system", "content": "You are an assistant that helps me polish research papers. Please re-organize my writing to make it sound logic."})
    content.append({"role": "user", "content": "Participants saved photo collections for significant events such as trips, ceremonies, and gatherings (see Table~\ref{tab:demographics}). These collections were typically taken with sighted help, and as a result, they knew little about the photo contents. Because their insufficient understanding , participants hoped to \textbf{thoroughly explore} each collection during reminiscence. However, this need was hardly fulfilled by their current practices. "})

    response = client.chat.completions.create(
                messages = content,
                model="gpt-4-vision-preview",
                max_tokens = 2000
            )

    reply = response.choices[0].message.content

    print(reply)