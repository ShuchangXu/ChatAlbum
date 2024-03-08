import os
import re
import json
import base64
import keyboard
import threading
from enum import Enum
from openai import OpenAI
from datetime import datetime

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

def human_check_reply(llm_reply, reply_type="reply"):
    print("\n【实验后台】Human Check LLM's {}:".format(reply_type), llm_reply)
    admin_input = input("【实验后台】Press \"Enter\" to accept, otherwise please input a corrected {}:".format(reply_type))
    reply = llm_reply
    
    if admin_input == "":
        print("【实验后台】LLM's {} is accepted.".format(reply_type))
        return reply
    else:
        print("【实验后台】Corrected {} is accepted.".format(reply_type))
        return admin_input


class BaselineFinal:
    #
    #
    # ________________________ Initialization ________________________
    def __init__(self, api_key, user, resume=None):
        if not resume:
            # ________ This is the Memory Tree ________
            # Photo Information
            self.user = user
            self.description = open(os.path.join(SCRIPT_DIR, "descriptions", "{}.txt".format(self.user)), 'r', encoding='utf-8').read()
            self.system_guide = open(os.path.join(SCRIPT_DIR, "prompts", "system_guide"), 'r', encoding='utf-8').read()
            self.retrieve_guide = open(os.path.join(SCRIPT_DIR, "prompts", "retrieve_guide"), 'r', encoding='utf-8').read()
            self.introduction_guide = open(os.path.join(SCRIPT_DIR, "prompts", "introduction_guide"), 'r', encoding='utf-8').read()
            
            # Chat History
            self.chat_history = []
            self.dialogue_turn = -1 # then it will be 0 for introduction
            
            #________ Log Content ________
            self.log = {
                "user": self.user,
                "resume": None,
                "datetime": datetime.now().strftime("%Y-%m-%d-%H:%M"),
                "chat_history": None,
                "reply_history": [],
                "description": self.description,
                "system_guide": self.system_guide,
                "retrieve_guide": self.retrieve_guide,
                "introduction_guide": self.introduction_guide
            }
            
        
        else:
            self.log = json.loads(open(os.path.join(SCRIPT_DIR, "logs", resume), 'r', encoding='utf-8').read())
            
            self.user = self.log["user"]
            self.chat_history = self.log["chat_history"]
            self.reply_history = self.log["reply_history"]
            self.description = self.log["description"]
            self.system_guide = self.log["system_guide"]
            self.retrieve_guide = self.log["retrieve_guide"]
            self.introduction_guide = self.log["introduction_guide"]
            
            self.dialogue_turn = self.reply_history[-1]["dialogue_turn"]
            
            self.log["datetime"] = datetime.now().strftime("%Y-%m-%d-%H:%M"),
            self.log["resume"] = resume              
        
        
        # ________ OpenAI client ________
        self.client = OpenAI(api_key=api_key, timeout=TIME_OUT)
        self.lock = threading.Lock()
        self.description_pieces = self.description.split("\n")
        
        # ______ Log Path _______
        log_prefix = self.user + '_' + datetime.now().strftime("%Y%m%d")
        log_postfix = 0        
        with self.lock:
            for filename in os.listdir(os.path.join(SCRIPT_DIR, "logs")):
                if filename.startswith(log_prefix):
                    log_postfix += 1
        self.log_path = os.path.join(SCRIPT_DIR, "logs", "{}_{}.log".format(log_prefix, log_postfix))
        with open(self.log_path, 'w', encoding='utf-8') as f:
            f.write(" ")
        
    #
    #
    # ________________________ Helper Functions ________________________
    def call_llm(self, content, max_tokens = 200, model="gpt-4-vision-preview"):
        response = self.client.chat.completions.create(
            messages = content,
            model = model,
            max_tokens = max_tokens
        )
        result = response.choices[0].message.content
        
        return result

    def record_current_dialogue_turn(self, user_input, raw_reply, reply, pics_id):
        self.dialogue_turn += 1
        self.log["reply_history"].append({
            "dialogue_turn": self.dialogue_turn,
            "user_input": user_input,
            "raw_reply": raw_reply,
            "reply": reply,
            "pics_id": pics_id
        })
        self.log["chat_history"] = self.chat_history
        
        if (self.dialogue_turn % 3) == 0 and self.dialogue_turn > 0:
            self.save_chat_history()
        
    def save_chat_history(self, log_path=None): 
        if not log_path:
            log_path = self.log_path
              
        self.log["chat_history"] = self.chat_history
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(json.dumps(self.log, ensure_ascii=False, indent=4))
        print("最新聊天记录已保存至", log_path)

    #
    #
    # ________________________ Replier ________________________
    
    def encode_image(self, image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')

    def replier(self, user_input, pics_id):
        content = [{
            "role": "system", 
            "content": self.system_guide + '\n' + \
                        self.description + '\n' + \
                        "以上为全部照片描述。请不要使用“第x张照片”、“这x张照片”等字眼。请确保你的回答不超过100个汉字。"
            }]
        content.extend(self.chat_history[(-6 if len(self.chat_history)>=6 else 0):])
        
        current_content = [{
                "type": "text",
                "text": ""
            }]  
        # description_that_has_me = []
        for pic_id in pics_id:
            photo_path = os.path.join(SCRIPT_DIR, "photos", self.user, str(pic_id)+".jpeg")
            try:
                base64_img = self.encode_image(photo_path)
            except Exception as e:
                print(e)
                print("编码照片{}失败，请查看路径是否正确，并决定是否中断实验重试。".format(photo_path))
                continue
            
            # current_piece = self.description_pieces[pic_id-1].split("\t")[-1]
            # if "你" in current_piece or "您" in current_piece:
            #     current_piece = current_piece.replace("你", "我")
            #     current_piece = current_piece.replace("您", "我")
            #     description_that_has_me.append(current_piece)
            
            current_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpg;base64,{base64_img}"
                    }
                })
            
        # if len(description_that_has_me) > 0:
        #     text_input = "{} 其中，我有出现的画面是：{}".format(user_input, ";".join(description_that_has_me))
        # else:
        #     text_input = "{} 请注意，我并没有出现在这几张照片中。".format(user_input)
        
        current_content[0]["text"] = user_input
        # print("vqa输入：", user_input)
        content.append({"role": "user", "content": current_content})
        
        reply = self.call_llm(content)  
        # print("GPT回复：", reply)          
        return reply
    
    
    def photo_retriever(self, user_input):
        content = [{
            "role": "system", 
            "content": self.retrieve_guide + '\n' + \
                        self.description + '\n' + \
                        "以上为全部照片描述。\n请确保返回格式为：[照片编号1, 照片编号2, ...]。" }]
        content.extend(self.chat_history[(-3 if len(self.chat_history)>=3 else 0):])
        content.append({"role": "user", "content": user_input})
        
        result = self.call_llm(content)        
        print("相关照片：", result)
        
        try:          
            pics_id = re.findall(r'\d+', result)
            pics_id = [int(id) for id in pics_id]
            if len(pics_id) > 3:
                pics_id = pics_id[:3]
            
        except Exception as e:
            print(e)
            pics_id = []
            
        return pics_id
    
    #
    #
    # ________________________ Response Functions ________________________
    def introduction(self):        
        content = [{"role": "system", "content": self.introduction_guide},
                   {"role": "user", "content": self.description}]
                #    {"role": "user", "content": "以上为全部照片的文字描述。你的回答不要超过100个汉字。"}]
        raw_reply = self.call_llm(content)
        reply = human_check_reply(raw_reply)
        
        self.chat_history.append({"role": "assistant", "content": reply})
        self.record_current_dialogue_turn(None, raw_reply, reply, [])

        return reply
    
    def chat(self, user_input):        
        pics_id = self.photo_retriever(user_input)
        raw_reply = self.replier(user_input, pics_id)
        reply = human_check_reply(raw_reply)

        self.chat_history.append({"role": "user", "content": user_input})
        self.chat_history.append({"role": "assistant", "content": reply})
        self.record_current_dialogue_turn(user_input, raw_reply, reply, pics_id)
        
        return reply