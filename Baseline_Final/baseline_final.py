import os
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
                "introduction_guide": self.introduction_guide
            }
            
        
        else:
            self.log = json.loads(open(os.path.join(SCRIPT_DIR, "logs", resume), 'r', encoding='utf-8').read())
            
            self.user = self.log["user"]
            self.chat_history = self.log["chat_history"]
            self.reply_history = self.log["reply_history"]
            self.description = self.log["description"]
            self.system_guide = self.log["system_guide"]
            self.introduction_guide = self.log["introduction_guide"]
            
            self.dialogue_turn = self.reply_history[-1]["dialogue_turn"]
            
            self.log["datetime"] = datetime.now().strftime("%Y-%m-%d-%H:%M"),
            self.log["resume"] = resume              
        
        
        # ________ OpenAI client ________
        self.client = OpenAI(api_key=api_key, timeout=TIME_OUT)
        self.lock = threading.Lock()
        
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

    def record_current_dialogue_turn(self, user_input, reply, pics_id):
        self.dialogue_turn += 1
        self.log["reply_history"].append({
            "dialogue_turn": self.dialogue_turn,
            "user_input": user_input,
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

    def replier(self, user_input):
        content = [{"role": "system", "content": self.system_guide},
                   {"role": "user", "content": self.description}]
        content.extend(self.chat_history[(-6 if len(self.chat_history)>=6 else 0):])
        content.append({"role": "user", "content": user_input})
        
        result = self.call_llm(content)
        print("GPT回复：", result)
        try:
            splits = result.split("-", 1)
            reply = splits[1]
            pics_id = splits[0]
        except Exception as e:
            print(e)
            reply = result
            pics_id = []
            
        return reply, pics_id
    
    #
    #
    # ________________________ Response Functions ________________________
    def introduction(self):        
        content = [{"role": "system", "content": self.introduction_guide},
                   {"role": "user", "content": self.description}]
        reply = "让我先概述一下相册的内容吧！" + self.call_llm(content)
        
        self.chat_history.append({"role": "assistant", "content": reply})
        self.record_current_dialogue_turn(None, reply, [])

        return reply
    
    def chat(self, user_input):
        reply, pics_id = self.replier(user_input)

        self.chat_history.append({"role": "user", "content": user_input})
        self.chat_history.append({"role": "assistant", "content": reply})
        self.record_current_dialogue_turn(user_input, reply, pics_id)
        
        return reply