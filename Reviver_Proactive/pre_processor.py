
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
    def __init__(self, api_key, user, old_mtree_file = None, has_meta_data = False):
        self.client = OpenAI(api_key=api_key, timeout=TIME_OUT)

        self.user = user
        self.photo_dir = os.path.join(SCRIPT_DIR, "photos", self.user)
        self.meta_data_list = None

        if has_meta_data:
            meta_data_json = json.loads(open(os.path.join(self.photo_dir, "meta_data.json"), 'r', encoding='utf-8').read())
            self.meta_data_list = meta_data_json["meta_data"]

        self.json_dir = os.path.join(SCRIPT_DIR, "mtree_json", self.user)
        self.mtree_save_path = os.path.join(self.json_dir, "memory_tree.json")

        if not os.path.exists(self.json_dir):
            os.makedirs(self.json_dir)

        if old_mtree_file is None:
            self.mtree = {
                "super_event":"",
                "events": [],
                "shorts": [],
                "photos": [],
                "topics": [],
                "ptexts": []
            }
        else:
            self.m_tree = json.loads(open(os.path.join(self.json_dir, old_mtree_file), 'r', encoding='utf-8').read())
        
        self.single_photo_prompt = open(os.path.join(SCRIPT_DIR, "prompts", "single_photo_extraction"), 'r', encoding='utf-8').read()
        self.slicing_prompt = open(os.path.join(SCRIPT_DIR, "prompts", "slicing"), 'r', encoding='utf-8').read()
    
    def save_m_tree(self, save_path=None): 
        if not save_path:
            save_path = self.mtree_save_path
        
        with open(save_path, 'w', encoding='utf-8') as f:
            f.write(json.dumps(self.mtree, ensure_ascii=False, indent=4))
        print("mtree已保存至", save_path)
    
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
        
    def vqa(self, prompt, pid, meta_data=""):
        current_content = [{
            "type": "text",
            "text": prompt,
        }]
        base64_usr = self.encode_image(os.path.join(self.photo_dir, "_.jpeg"))
        current_content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpg;base64,{base64_usr}"
            }
        })
        
        base64_img = self.encode_image(os.path.join(self.photo_dir, str(pid)+".jpeg"))
            
        current_content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpg;base64,{base64_img}"
            }
        })

        current_content.append({
            "type": "text",
            "text": "the meta data of the second picture is:" + meta_data
        })

        content = [
            {"role": "user", "content": current_content}
        ]

        reply_string = self.call_llm(content)
        print(reply_string+",")

        reply_dict = json_parser(reply_string)

        return reply_dict
    
    def single_photo_extraction(self, pid):
        meta_data = ""
        if self.meta_data_list is not None:
            meta_data = self.meta_data_list[pid]

        reply_dict = self.vqa(self.single_photo_prompt, pid, meta_data)

        return reply_dict
    
    def batch_photo_extraction(self, pid_bgn, p_cnt):
        for pid in range(pid_bgn, pid_bgn + p_cnt):
            ptext = self.single_photo_extraction(pid)
            self.mtree["ptexts"].append(ptext)

    # def slice(self):
    #     content = []
    #     task = self.slicing_prompt + json.dumps(self.mtree['ptexts'])
    #     content.append({"role": "user", "content": task})

    #     reply_string = self.call_llm(content)

    #     idx_bgn_list = [int(e) if e.isdigit() else e for e in reply_string.split(',')]
    #     idx_end_list = [for e in idx_bgn_list][1:]
    #     idx_end_list.append(len(self.mtree['ptexts']))



    #     return reply_dict

        
    
    # def build_m_tree(self, ):
    #     events = []
    #     shorts = []
    #     photos = []
    #     topics = []
    #     return 