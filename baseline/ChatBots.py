import os
import re
import time
import json
import base64
import threading
from PIL import Image
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

import boto3
from boto3 import Session


MAX_ATTEMPTS = 3
TIME_OUT = 30

class BaselineChatBot:
    def __init__(self, api_key, model="gpt-4-vision-preview", max_tokens=200, user='anonymous', resume=None) -> None:
        if resume:
            print("读取{}历史记录，将在从过往中断处继续".format(resume))
            self.log = json.loads(open("./logs/" + resume, 'r', encoding='utf-8').read())
            
            self.model = self.log["model"]
            self.max_tokens = self.log["max_tokens"]
            self.user = self.log["user"]
            
            self.system_guide = self.log["system_guide"]
            self.vqa_guide = self.log["vqa_guide"]
            self.evaluator_guide = self.log["evaluator_guide"]
            self.photo_description = self.log["photo_description"]
            
            self.content = self.log["content"]  
            
            self.log["date"] = datetime.now().strftime("%Y-%m-%d")
            
        else:
            self.model = model
            self.max_tokens = max_tokens
            self.user = user
            
            self.system_guide = open("./prompts/system_guide", 'r', encoding='utf-8').read()
            self.vqa_guide = open("./prompts/vqa_guide", 'r', encoding='utf-8').read()
            self.evaluator_guide = open("./prompts/evaluator_guide", 'r', encoding='utf-8').read()   
            self.photo_description = open("./photos/photo_description", 'r', encoding='utf-8').read()  
            
            self.content = [
                                {"role": "system", "content": self.system_guide},
                                {"role": "user", "content": self.photo_description},
                            ]
            self.log = {
                "user": self.user,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "model": self.model,
                "max_tokens": self.max_tokens,
                
                "system_guide": self.system_guide,
                "vqa_guide": self.vqa_guide,
                "evaluator_guide": self.evaluator_guide,
                "photo_description": self.photo_description,
                "content": None,
                "chat_history": [],
            }
        
        
        self.client = OpenAI(api_key=api_key, timeout=TIME_OUT)         
        self.evaluator = Evaluator(api_key, self.model, self.max_tokens, self.user, self.evaluator_guide)
        self.vqa = VQAChatBot(api_key, self.model, self.max_tokens*3, self.user, self.vqa_guide)  
        
        self.lock = threading.Lock()
        
        
    
    def single_round_chat(self, user_input):        
        self.content.append({
            "role": "user", "content": user_input
        })        
        
        
        attempt_count = 0
        while attempt_count < MAX_ATTEMPTS:
            try:                
                start_time = time.time()
                response = self.client.chat.completions.create(
                        model = self.model,
                        max_tokens = self.max_tokens,
                        messages = self.content
                        )
                end_time = time.time()
                
                try:
                    json_response = json.loads(response.choices[0].message.content)
                except:
                    json_lines = response.choices[0].message.content.split("\n")[1:-1]
                    json_response = json.loads(" ".join(json_lines))
                break
                
            except Exception as e:
                print(e)
                print("ChatBot GPT回复读取失败，原回复如下:")
                print(response.choices[0].message.content)
                try:
                    json_response = json.loads(input("请选出reply与relevant_pics内容，以json格式输入: "))
                    break
                
                except:
                    attempt_count += 1
                    if attempt_count < MAX_ATTEMPTS:
                        print("读取GPT回复失败，重新尝试...")
                    else:
                        print("读取GPT回复失败，保存记录后将退出")
                        print(response.choices[0].message.content)
                        self.save_chat_history()
                        return False                  
                
                
                    
                
        reply = json_response["reply"]
        relevant_pics = json_response["relevant_pics"]
        
        
        print("请求用时:", "{}s".format(round(end_time - start_time, 3)))
        print("GPT回复:", reply)
        print("相关图片:", relevant_pics)
        
        verified, reason = self.evaluator.check("Question: {}\nAnswer: {}".format(user_input, reply))
        current_record = {
            "user_input": user_input,
            "chatbot_reply": reply,
            "chatbot_timecost": {
                                    "duration_ms": int((end_time - start_time) * 1000),
                                    "input_token": response.usage.prompt_tokens,
                                    "output_token": response.usage.completion_tokens
                                },
            "relevant_pics": relevant_pics,
            
            "evaluator_result": verified,
            "evaluator_reason": reason,
            
            "vqa_reply": None,
            "vqa_timecost": None,
        }
        
        vqa_reply = None
        if not verified:
            print("Need to retrieve photos!")
            vqa_reply, vqa_timecost = self.vqa.visual_question_answer(user_input, relevant_pics)
            current_record["vqa_reply"] = vqa_reply
            current_record["vqa_timecost"] = vqa_timecost
            
        self.content.append({
            "role": "assistant", "content": vqa_reply if vqa_reply else reply
        })
        self.log["chat_history"].append(current_record)

        return True
            
    
    def save_chat_history(self):
        self.log["content"] = self.content        
        log_data = json.dumps(self.log, ensure_ascii=False, indent=4)
        log_prefix = self.user + '_' + datetime.now().strftime("%Y%m%d")
        log_postfix = 0        
        with self.lock:
            for filename in os.listdir("./logs"):
                if filename.startswith(log_prefix):
                    log_postfix += 1
        log_path = "./logs/{}_{}.log".format(log_prefix, log_postfix)

        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(log_data)
        print("本次聊天记录已保存至", log_path)



class HierarchyChatBot:
    def __init__(self, api_key, model="gpt-4-vision-preview", max_tokens=200, user='anonymous', resume=None) -> None:
        if resume:
            print("读取{}历史记录，将在从过往中断处继续".format(resume))
            self.log = json.loads(open("./logs/" + resume, 'r', encoding='utf-8').read())
            
            self.model = self.log["model"]
            self.max_tokens = self.log["max_tokens"]
            self.user = self.log["user"]
            
            self.hierarchy_guide = self.log["hierarchy_guide"]
            self.attention_guide = self.log["attention_guide"]
            self.slices = self.log["slices"]            
            self.content = self.log["content"]  
            
            self.log["date"] = datetime.now().strftime("%Y-%m-%d")
            
        else:
            self.model = model
            self.max_tokens = max_tokens
            self.user = user
            
            self.hierarchy_guide = open("./prompts/hierarchy_guide", 'r', encoding='utf-8').read()
            self.attention_guide = open("./prompts/attention_guide", 'r', encoding='utf-8').read()
            self.photos_info = json.loads(open("./photos/text_des_P7.json", 'r', encoding='utf-8').read())
            
            self.content = [{"role": "system", "content": self.hierarchy_guide}]
            self.log = {
                "user": self.user,
                "date": datetime.now().strftime("%Y-%m-%d"),
                "model": self.model,
                "max_tokens": self.max_tokens,
                
                "hierarchy_guide": self.hierarchy_guide,
                "attention_guide": self.attention_guide,
                "photos_info": self.photos_info,
                "content": None,
                "chat_history": [],
            }
        
        self.client = OpenAI(api_key=api_key, timeout=TIME_OUT)  
        self.attention_detector = AttentionDetector(api_key, self.model, self.max_tokens, self.user, self.attention_guide)         
        self.lock = threading.Lock()
        
    
    def single_round_chat(self, user_input):
        self.content.append({
            "role": "user", "content": user_input
        })
        scene, object, pics = self.attention_detector.single_round_detect(user_input)
        pics_info = ""
        for pic in pics:
            pic_info = json.dumps({
                str(pic): self.photos_info[str(pic)]
            }, ensure_ascii=False)
            pics_info += (pic_info + '\n')
            
        if len(pics_info) == 0:
            pics_info = "相册浏览完毕，请询问用户是否继续浏览。"
        
        
        current_content = self.content
        current_content.append({
            "role": "user", "content": pics_info
        })        
        
        
        attempt_count = 0
        while attempt_count < MAX_ATTEMPTS:
            try:                
                start_time = time.time()
                response = self.client.chat.completions.create(
                        model = self.model,
                        max_tokens = self.max_tokens,
                        messages = current_content
                        )
                end_time = time.time()
                
                try:
                    json_response = json.loads(response.choices[0].message.content)
                except:
                    json_lines = response.choices[0].message.content.split("\n")[1:-1]
                    json_response = json.loads(" ".join(json_lines))
                break
                
            except Exception as e:
                print(e)
                print("HierarchyChatBot GPT回复读取失败，原回复如下:")
                print(response.choices[0].message.content)
                try:
                    json_response = json.loads(input("请选出reply与relevant_pics内容，以json格式输入: "))
                    break
                
                except:
                    attempt_count += 1
                    if attempt_count < MAX_ATTEMPTS:
                        print("读取GPT回复失败，重新尝试...")
                    else:
                        print("读取GPT回复失败，保存记录后将退出")
                        print(response.choices[0].message.content)
                        self.save_chat_history()
                        return False                  
                                    
                
        reply = json_response["reply"]
        relevant_pics = json_response["relevant_pics"]
        
        
        print("请求用时:", "{}s".format(round(end_time - start_time, 3)))
        print("GPT回复:", reply)
        print("相关图片:", relevant_pics)
        
        current_record = {
            "user_input": user_input,
            "current_scene": scene,
            "current_object": object,
            "object_pics": pics,
            "chatbot_reply": reply,
            "chatbot_timecost": {
                                    "duration_ms": int((end_time - start_time) * 1000),
                                    "input_token": response.usage.prompt_tokens,
                                    "output_token": response.usage.completion_tokens
                                },
            "relevant_pics": relevant_pics,
        }
        
        self.content.append({
            "role": "assistant", "content": reply
        })
        self.log["chat_history"].append(current_record)

        return True
    
           
    
    def save_chat_history(self):
        self.log["content"] = self.content        
        log_data = json.dumps(self.log, ensure_ascii=False, indent=4)
        log_prefix = self.user + '_' + datetime.now().strftime("%Y%m%d")
        log_postfix = 0        
        with self.lock:
            for filename in os.listdir("./logs"):
                if filename.startswith(log_prefix):
                    log_postfix += 1
        log_path = "./logs/{}_{}.log".format(log_prefix, log_postfix)

        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(log_data)
        print("本次聊天记录已保存至", log_path)
        
        
        
        
        
class AttentionDetector:
    def __init__(self, api_key, model, max_tokens, user, attention_guide) -> None:
        self.client = OpenAI(api_key=api_key, timeout=TIME_OUT)
        self.model = model
        self.max_tokens = max_tokens
        self.user = user
        
        self.slices = json.loads(open("./photos/slices.json", 'r', encoding='utf-8').read())
        self.process_slices()
        self.attention_guide = attention_guide
        self.content = [
            {"role": "system", "content": self.attention_guide + '\n' + self.slices}
        ]
        
    
    def process_slices(self):
        result = ""
        for _, value in self.slices.items():
            title = value["tit"]
            objects = value["obj"]
            indexes = value["ind"]            
            piece = title + ": "
            for i in range(len(objects)):
                piece += (objects[i] + indexes[i])
                if i < len(objects) - 1:
                    piece += ", "
                else:
                    piece += '\n'
            
            result += piece
        self.slices = result
        print(self.slices)
        
    
    def single_round_detect(self, user_input=None):
        if user_input:
            self.content.append({
                "role": "system", "content": user_input
            })
        
        attempt_count = 0
        while attempt_count < MAX_ATTEMPTS:
            try:
                response = self.client.chat.completions.create(
                                model = self.model,
                                max_tokens = self.max_tokens,
                                messages = self.content
                            )
                
                try:
                    json_response = json.loads(response.choices[0].message.content)
                except:
                    json_lines = response.choices[0].message.content.split("\n")[1:-1]
                    json_response = json.loads(" ".join(json_lines))
                break
                    
            except Exception as e:
                print(e)
                print("Attention GPT回复读取失败，原回复如下:")
                print(response.choices[0].message.content)
                try:
                    json_response = json.loads(input("请选出scene、object与pics内容，以json格式输入: "))
                    break
                
                except:
                    attempt_count += 1
                    if attempt_count < MAX_ATTEMPTS:
                        print("读取GPT回复失败，重新尝试...")
                    else:
                        return None
                    
        self.content.append({
            "role": "assistant", "content": response.choices[0].message.content
        })
        print(json_response)
        return json_response["scene"], json_response["object"], json_response["pics"]
        
            
        





class VQAChatBot:
    def __init__(self, api_key, model, max_tokens, user, vqa_guide) -> None:
        self.client = OpenAI(api_key=api_key, timeout=TIME_OUT)
        self.model = model
        self.max_tokens = max_tokens
        self.user = user
        
        self.vqa_guide = vqa_guide
        self.content = [
            {"role": "system", "content": self.vqa_guide},
            {"role": "user", "content": ""}
        ]          
        
        self.photo_list = sorted(os.listdir("./photos/" + self.user))
        
    
    
    def encode_image(self, image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
        
        
    
    def visual_question_answer(self, user_input, relevant_pics):
        print("=== Retrieving ===")
        current_content = [{
            "type": "text",
            "text": user_input,
        }]
        
        for id in relevant_pics:
            photo_name = self.photo_list[id - 1]                
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
        return reply, timecost
    


class Evaluator:
    def __init__(self, api_key, model, max_tokens, user, evaluator_guide) -> None:
        self.client = OpenAI(api_key=api_key, timeout=TIME_OUT)
        self.model = model
        self.max_tokens = max_tokens
        self.user = user
        
        self.evaluator_guide = evaluator_guide
        self.content = [
            {"role": "system", "content": self.evaluator_guide},
            {"role": "user", "content": ""}
        ]
        
    
    def check(self, dialogue):
        print("=== Evaluating ===")
        self.content[-1]["content"] = dialogue
        print(dialogue)
        
        attempt_count = 0
        while attempt_count < MAX_ATTEMPTS:
            try:
                response = self.client.chat.completions.create(
                                model = self.model,
                                max_tokens = self.max_tokens,
                                messages = self.content
                            )
                
                try:
                    json_response = json.loads(response.choices[0].message.content)
                except:
                    json_lines = response.choices[0].message.content.split("\n")[1:-1]
                    json_response = json.loads(" ".join(json_lines))
                break
                    
            except Exception as e:
                print(e)
                print("Evaluator GPT回复读取失败，原回复如下:")
                print(response.choices[0].message.content)
                try:
                    json_response = json.loads(input("请选出reply与relevant_pics内容，以json格式输入: "))
                    break
                
                except:
                    attempt_count += 1
                    if attempt_count < MAX_ATTEMPTS:
                        print("读取GPT回复失败，重新尝试...")
                    else:
                        return None, None
           
                
        result = json_response["result"]
        reason = json_response["reason"]
        print("检验结果:", result)
        if not result:
            print("判断理由:", reason)
        print("==================")
        return result, reason