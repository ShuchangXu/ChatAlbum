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


class BaselineChatBot:
    def __init__(self, api_key, model, max_tokens, user='anonymous') -> None:
        self.client = OpenAI(api_key=api_key, timeout=600)         
        self.evaluator = Evaluator(api_key, model, max_tokens)
        self.vqa = VQAChatBot(api_key, model, max_tokens*3, user)
           
        self.model = model
        self.max_tokens = max_tokens
        self.user = user
        self.system_guide = open("./prompts/system_guide", 'r', encoding='utf-8').read()
        self.photo_description = open("./photos/photo_description", 'r', encoding='utf-8').read()
        self.content = [
                            {"role": "system", "content": self.system_guide},
                            {"role": "user", "content": self.photo_description},
                        ]
        self.time_cost = []
        self.lock = threading.Lock()
        
        
    
    def single_round_chat(self, user_input):
        self.content.append({
            "role": "user", "content": user_input
        })
        
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
            try:
                json_response = json.loads(response.choices[0].message.content[8:-4])
            except Exception as e:
                print(response.choices[0].message.content)
                self.save_chat_history()
                print(e)
                
        reply = json_response["reply"]
        relevant_pics = json_response["relevant_pics"]
        
        
        print("请求用时:", "{}s".format(round(end_time - start_time, 3)))
        print("GPT回复:", reply)
        print("相关图片:", relevant_pics)
        
        verified = self.evaluator.check("Question: {}\nAnswer: {}".format(user_input, reply))
        if not verified:
            print("Need to retrieve photos!")
            reply, start_time, end_time = self.vqa.visual_question_answer(user_input, relevant_pics)
            
            
        self.time_cost.append({
            "duration_ms": int((end_time - start_time) * 1000),
            "input_token": response.usage.prompt_tokens,
            "output_token": response.usage.completion_tokens
        })
        
        self.content.append({
            "role": "assistant", "content": reply
        })
            
            
        
    
    def save_chat_history(self):
        log_data = json.dumps({
            "user": self.user,
            "model": self.model,
            "chat_history": self.content,
            "time_cost": self.time_cost
        }, ensure_ascii=False, indent=4)
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
    def __init__(self, api_key, model, max_tokens, user) -> None:
        self.client = OpenAI(api_key=api_key, timeout=600)
        self.model = model
        self.max_tokens = max_tokens
        self.user = user
        
        self.vqa_guide = open("./prompts/vqa_guide", 'r', encoding='utf-8').read()
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
        response = self.client.chat.completions.create(
                model = self.model,
                max_tokens = self.max_tokens,
                messages = self.content
                )
        end_time = time.time()
        reply = response.choices[0].message.content 
        print("请求用时:", "{}s".format(round(end_time - start_time, 3)))
        print("GPT回复:", reply)
        print("==================")
        return reply, start_time, end_time
    


class Evaluator:
    def __init__(self, api_key, model, max_tokens, user='evaluator') -> None:
        self.client = OpenAI(api_key=api_key, timeout=600)
        self.model = model
        self.max_tokens = max_tokens
        self.evaluator_guide = open("./prompts/evaluator_guide", 'r', encoding='utf-8').read()
        self.content = [
            {"role": "system", "content": self.evaluator_guide},
            {"role": "user", "content": ""}
        ]
        
    
    def check(self, dialogue):
        print("=== Evaluating ===")
        self.content[-1]["content"] = dialogue
        print(dialogue)
        
        response = self.client.chat.completions.create(
                model = self.model,
                max_tokens = self.max_tokens,
                messages = self.content
                )
        
        try:
            json_response = json.loads(response.choices[0].message.content)
        except:
            json_response = json.loads(response.choices[0].message.content[8:-4])
        result = json_response["result"]
        reason = json_response["reason"]
        print("检验结果:", result)
        if not result:
            print("判断理由:", reason)
        print("==================")
        return result