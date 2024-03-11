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
    content.append({"role": "user", "content": "The growing accessibility of photo taking \cite{gonzalez_penuela_understanding_2022,iwamura_visphoto_2020,bennett_how_2018,adams_blind_2016,harada2013accessible} and sharing \cite{zhao2017effect,mathur_mixed_ability_2018} leads to an increase in the number of photos PVI can capture and collect. In fact, the size of their personal photo collections can be larger than 30,000 for some PVI \cite{jung_so_2022}.\
                    To improve the accessibility of photo collections, researchers have explored methods to help PVI identify each photo after photo-taking. For example, accessible photo album \cite{harada2013accessible} proposed attaching audio recordings to each photo. \cite{jung_so_2022} investigated how want image descriptions for different images. While help identify and understand each separate photo, little work examined the challenges of understanding a photo collection.\
                    A collection of photos holds more information than each separate photo. Several aspects of such information have been studied in computer vision. For example, visual storytelling \cite{} aims to build a coherent story from several images. Multi-image VQA \cite{} aims to how . Yet, these works are technical , little tested with PVI. It is unclear the needs and information wants PVI want when understanding a photo collection.\
                    Our work fills this gap by consulting with PVI to understand . Our reveals the need to get a comprehensive understanding of the photo collection. So go far beyond ask questions. They need to be guided to explore details."})

    response = client.chat.completions.create(
                messages = content,
                model="gpt-4-vision-preview",
                max_tokens = 2000
            )

    reply = response.choices[0].message.content

    print(reply)