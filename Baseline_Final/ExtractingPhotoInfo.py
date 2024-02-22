import os
import time
import json
import base64
from dotenv import load_dotenv
from openai import OpenAI

MAX_TOKENS = 1000
MAX_ATTEMPTS = 3
TIME_OUT = 30
MODEL = "gpt-4-vision-preview"

SCRIPT_PATH = os.path.abspath(__file__)
SCRIPT_DIR = os.path.dirname(SCRIPT_PATH)

class Photo_PreProcessor:
    def __init__(self, api_key, model, max_tokens, user, description_guide) -> None:
        self.client = OpenAI(api_key=api_key, timeout=TIME_OUT)
        self.model = model
        self.max_tokens = max_tokens
        self.user = user
        
        self.description_guide = description_guide
        self.content = [
            {"role": "system", "content": self.description_guide},
            {"role": "user", "content": ""}
        ]          
        
    
    
    def encode_image(self, image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
        
        
    def photo_captioning(self, photo_path, user_photo_path):
        print(photo_path)
        current_content = []        
        
        base64_user = self.encode_image(user_photo_path)
        current_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpg;base64,{base64_user}"
                }
            })
        
        base64_img = self.encode_image(photo_path)
        current_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpg;base64,{base64_img}"
                }
            })
            
        self.content[-1]["content"] = current_content
        response = self.client.chat.completions.create(
                    model = self.model,
                    max_tokens = self.max_tokens,
                    messages = self.content
        )
        
        reply = response.choices[0].message.content 
        print(reply)
        # print("请求用时:", "{}s".format(round(end_time - start_time, 3)))
        # print("GPT回复:", reply)
        # print("==================")
        # timecost = {
        #                 "duration_ms": int((end_time - start_time) * 1000),
        #                 "input_token": response.usage.prompt_tokens,
        #                 "output_token": response.usage.completion_tokens
        #             },
        # with open("./photos/{}_photo_des".format(self.user), 'a', encoding='utf-8') as f:
        #     f.write(photo_name + reply)
        # print("已保存")
        return reply



if __name__ == "__main__":
    load_dotenv()
    api_key=os.getenv("GPT_API_KEY")
    user = "zhy_2"
    
    des_extraction_guide = open(os.path.join(SCRIPT_DIR, "prompts", "photo_des_guide"), 'r', encoding='utf-8').read()
    Processor = Photo_PreProcessor(api_key, MODEL, MAX_TOKENS, user, des_extraction_guide)
    
    photo_dir = os.path.join(SCRIPT_DIR, "photos", user)
    photo_names = os.listdir(photo_dir)
    descriptions = []
    
    user_photo_path = os.path.join(photo_dir, photo_names[-1])
    photo_names = sorted(photo_names[:-1], key=lambda x: int(x.split('.')[0]))
    
    
    for photo_name in photo_names:
        photo_path = os.path.join(photo_dir, photo_name)
        description = Processor.photo_captioning(photo_path, user_photo_path)
        descriptions.append(description)
    
    print(descriptions)
    
    with open(os.path.join(SCRIPT_DIR, "descriptions", "{}.txt".format(user)), "w", encoding='utf-8') as f:
        for i, description in enumerate(descriptions):
            f.write("{}\t{}\n".format(i+1, description))
    