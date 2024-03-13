import os
import time
import json
import base64
from dotenv import load_dotenv
from openai import OpenAI

MAX_TOKENS = 1000
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
        # print(photo_path)
        current_content = [{
            "type": "text",
            "text": "请注意，第一张照片是我，仅作为人脸的参考，第二张照片才是你需要描述的图片。切勿描述第二张照片之外的内容，切勿出现第几张照片等字眼。",
        }]        
        
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
        
        attempt_times = 3
        attempt_count = 0
        
        while attempt_count < attempt_times:
            attempt_count += 1
            response = self.client.chat.completions.create(
                        model = self.model,
                        max_tokens = self.max_tokens,
                        messages = self.content
            )
            
            reply = response.choices[0].message.content 
            print(reply)
            
            if "第一张" in reply or "第二张" in reply:
                if attempt_count < attempt_times:
                    print("Photo caption有误，将再次尝试({}/{})".format(attempt_count, attempt_times))
                else:
                    print("Photo caption有误，请手动修正({}/{})".format(attempt_count, attempt_times))
            else:
                break
        
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
    user = "zouchao_1"
    
    des_extraction_guide = open(os.path.join(SCRIPT_DIR, "prompts", "photo_des_guide"), 'r', encoding='utf-8').read()
    Processor = Photo_PreProcessor(api_key, MODEL, MAX_TOKENS, user, des_extraction_guide)
    
    photo_dir = os.path.join(SCRIPT_DIR, "photos", user)
    photo_names = os.listdir(photo_dir)
    descriptions = []
    
    start_from = 1 #从第一张图片开始
        
    user_photo_path = os.path.join(photo_dir, '_.jpeg')    
    photo_names = sorted([name for name in photo_names if "_" not in name], key=lambda x: int(x.split('.')[0]))
    photo_names = photo_names[start_from-1:]
    
    
    for photo_name in photo_names:
        print(photo_name)
        photo_path = os.path.join(photo_dir, photo_name)
        try:
            description = Processor.photo_captioning(photo_path, user_photo_path)
            descriptions.append(description)
        except Exception as e:
            print(e)
            print("{}识别失败，程序将退出，请手动修改start_from，从该张图片起重新操作。重新操作前务必保存此前图片描述文档至其他名称文件中。")
            break
            
    
    with open(os.path.join(SCRIPT_DIR, "descriptions", "{}.txt".format(user)), "w", encoding='utf-8') as f:
        for i, description in enumerate(descriptions):
            f.write("{}\t{}\n".format(i+1, description))
        
    