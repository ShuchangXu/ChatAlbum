
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

def console_log(log):
    print("Debug Log:" + log)

def json_parser(content):
    try:
        json_response = json.loads(content)
    except:
        json_lines = content.split("\n")[1:-1]
        json_response = json.loads(" ".join(json_lines))
    
    return json_response

class Photo_PreProcessor:
    def __init__(self, api_key, user):
        self.user = user
        self.client = OpenAI(api_key=api_key, timeout=TIME_OUT)
        
        self.photo_list = sorted(os.listdir("./photos/" + self.user))
        
    def call_llm(self, content, max_tokens = MAX_TOKENS, model="gpt-4-vision-preview"):
        response = self.client.chat.completions.create(
            messages = content,
            model = model,
            max_tokens = max_tokens
        )

        reply = response.choices[0].message.content
        return reply
    
    def encode_image(self, image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
        
    def add_relevant_photo(self):
        current_content = [{
            "type": "text",
            "text": "下面照片中, 第一张是用户的正面照，请记住这是用户本人。第二张到最后一张照片，是你用来回答后续问题时的照片。",
        }]
        base64_usr = self.encode_image(os.path.join(self.photo_dir, "_.jpeg"))
        current_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpg;base64,{base64_usr}"
                }
            })
        
        for pid in self.photos[self.curEid]:
            base64_img = self.encode_image(os.path.join(self.photo_dir, str(pid)+".jpeg"))
                
            current_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpg;base64,{base64_img}"
                    }
                })
        return current_content
    
    def visual_question_answer(self, user_input, id):
        print("=== Retrieving ===")
        current_content = [{
            "type": "text",
            "text": user_input,
        }]
        
        base64_usr = self.encode_image(os.path.join("./photos", self.user, "_.jpeg"))
        current_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpg;base64,{base64_usr}"
                }
            })

        photo_name = self.photo_list[id]
        photo_path = os.path.join("./photos", self.user, photo_name)
        
        base64_img = self.encode_image(photo_path)
            
        current_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpg;base64,{base64_img}"
                }
            })
            
        
        start_time = time.time()
        self.content[-1]["content"] = current_content
        try:
            response = self.client.chat.completions.create(
                    model = self.model,
                    max_tokens = self.max_tokens,
                    messages = self.content
                    )
        except:
            print("请求GPT-4v失败...")
            return None, None
        end_time = time.time()
        
        reply = response.choices[0].message.content 
        print("请求用时:", "{}s".format(round(end_time - start_time, 3)))
        print("GPT回复:", reply)
        print("==================")
        timecost = {
                        "duration_ms": int((end_time - start_time) * 1000),
                        "input_token": response.usage.prompt_tokens,
                        "output_token": response.usage.completion_tokens
                    },
        with open("./photos/{}_photo_des".format(self.user), 'a', encoding='utf-8') as f:
            f.write(photo_name + reply)
        print("已保存")
        return reply, photo_name, timecost
    
    # def save_reply(self, reply, photo_name): 
    #     with open("./photos/{}_photo_5W".format(self.user), 'a', encoding='utf-8') as f:
    #         f.write(photo_name + reply)
    #     print("已保存")



if __name__ == "__main__":
    load_dotenv()
    api_key=os.getenv("OPENAI_API_KEY")
    event_extraction_guide = open("./prompts/photo_event_guide", 'r', encoding='utf-8').read()
    des_extraction_guide = open("./prompts/photo_des_guide", 'r', encoding='utf-8').read()
    Processor = Photo_PreProcessor(api_key, MODEL, MAX_TOKENS, "dev3", des_extraction_guide)

    for i in range(1, 30):
        reply= Processor.visual_question_answer("",i)
        # Processor.save_reply(reply, photo_name)