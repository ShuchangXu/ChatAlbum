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
        # log_data = json.dumps({
        #     "user": self.user,
        #     "model": self.model,
        #     "chat_history": self.content,
        #     "time_cost": self.time_cost
        # }, ensure_ascii=False, indent=4)
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
        self.bucket = "vislabttsasr"
        self.s3 = boto3.client("s3")
    #     self.change_bucket_policy()
        
            
    # def __del__(self):
    #     self.s3.delete_bucket_policy(Bucket=self.bucket)
    #     print("Deleted s3 bucket policy")
        
    
    def change_bucket_policy(self):
        bucket_policy = {
                            "Version": "2012-10-17",
                            "Id": "Policy",
                            "Statement": [
                                {
                                    "Sid": "Stmt",
                                    "Effect": "Allow",
                                    "Principal": "*",
                                    "Action": "s3:GetObject",
                                    "Resource": "arn:aws:s3:::" + self.bucket + "/*"
                                }
                            ]
                        }
        self.s3.put_bucket_policy(
            Bucket=self.bucket,
            Policy=json.dumps(bucket_policy)
        )
        
    
    def visual_question_answer(self, user_input, relevant_pics):
        print("=== Retrieving ===")
        current_content = [{
            "type": "text",
            "text": user_input,
        }]
        
        for id in relevant_pics:
            photo_name = self.photo_list[id - 1]                
            photo_path = os.path.join("./photos", self.user, photo_name)
            
            key = "{}_{}.jpg".format(self.user, id)
            try:
                self.s3.head_object(Bucket=self.bucket, Key=key)
            except:
                self.s3.upload_file(Filename=photo_path, Key=key, Bucket=self.bucket)
            
            img_url = f"https://{self.bucket}.s3.amazonaws.com/{key}"
            print(img_url)
                
            current_content.append({
                "type": "image_url",
                "image_url": {
                    "url": img_url
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