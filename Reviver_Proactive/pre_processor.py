
import os
import json
import base64

from openai import OpenAI

MAX_TOKENS = 1000
TIME_OUT = 30

SCRIPT_PATH = os.path.abspath(__file__)
SCRIPT_DIR = os.path.dirname(SCRIPT_PATH)

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
        self.client = OpenAI(api_key=api_key, timeout=TIME_OUT)

        self.user = user
        self.photo_dir = os.path.join(SCRIPT_DIR, "photos", self.user)
        self.json_dir = os.path.join(SCRIPT_DIR, "mtree_json", self.user)

        self.single_photo_prompt = open(os.path.join(SCRIPT_DIR, "prompts", "single_photo_extraction"), 'r', encoding='utf-8').read()

        self.mtree = {}
        self.mtree["ptext_list"] = []
        self.mtree["photos"] = []
        
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
        
    def vqa(self, task, pid_list):
        current_content = [{
            "type": "text",
            "text": task,
        }]
        base64_usr = self.encode_image(os.path.join(self.photo_dir, "_.jpeg"))
        current_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpg;base64,{base64_usr}"
                }
            })
        
        for pid in pid_list:
            base64_img = self.encode_image(os.path.join(self.photo_dir, str(pid)+".jpeg"))
                
            current_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpg;base64,{base64_img}"
                    }
                })
            
        content = [
            {"role": "user", "content": current_content}
        ]

        reply_string = self.call_llm(content)

        reply_dict = json_parser(reply_string)

        return reply_dict

    
    def single_photo_extraction(self, pid):
        reply_dict = self.vqa(self.single_photo_prompt, [pid])
        return reply_dict
    
    def all_photo_extraction(self, pid_bgn, p_cnt):
        self.mtree["ptext_list"] = []
        for pid in range(pid_bgn, pid_bgn + p_cnt):
            ptext = self.single_photo_extraction(pid)
            self.mtree["ptext_list"].append(ptext)


    def slice(self):
        self.mtree["ptext_list"]
        p_
        if
        return 
        
    
    def build_m_tree(self, ):
        events = []
        shorts = []
        photos = []
        topics = []
        return 