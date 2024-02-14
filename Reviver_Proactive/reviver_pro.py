import os
import json
import base64
import threading
from openai import OpenAI
from datetime import datetime

TIME_OUT = 30

def console_log(log):
    print("Debug Log:" + log)

def json_parser(content):
    try:
        json_response = json.loads(content)
    except:
        json_lines = content.split("\n")[1:-1]
        json_response = json.loads(" ".join(json_lines))
    
    return json_response

class ReviverPro:
    #
    #
    # ________________________ Initialization ________________________
    def __init__(self, api_key):
        # ________ This is the Memory Tree ________
        # Photo Information
        self.superE = None #"18年秋天，在青岛拍摄，一共有25张照片。其中有XXX，XXX等场景。"
        self.evtCnt = 0 # number of events
        self.events = None
        self.topics = None
        self.photos = None
        
        # User Narrations
        self.event_narrations = None

        # ________ These variables tracked the progress ________
        self.curEid = 0
        self.suggSummary = False
        self.suggNextEvent = False
        self.isTopicTalked = None

        # Chat History
        self.chat_history = []

        # ________ OpenAI client ________
        self.client = OpenAI(api_key=api_key, timeout=TIME_OUT)
        self.lock = threading.Lock()

        # ________ User Info ________
        self.user = None
        self.photo_dir = None
    
    def init_mtree(self, user="dev0214"):
        self.user = user
        self.photo_dir = "./Reviver_Proactive/photos/" + self.user

        self.superE = "这是一九年6月底,你在香港和广州拍摄的照片，一共有11张。其中有你在香港市区的拍照留念，有你在维多利亚港和朋友的合影，还有飞机和蓝天白云的照片。"
        self.events = ["第一个场景,是你在香港市区街道上的拍照留念，一共有4张照片。看起来像是你在市区游玩了一整天。",
                       "第二个场景,是你在维多利亚港和朋友们的合影，一共有4张照片。既有夜景海港，对面霓虹灯闪烁；又有白天的海港。",
                       "第三个场景,是乘坐飞机和汽车的照片，一共有4张。前两张是拍摄的飞机，似乎是在候机大厅。后两张拍摄的蓝天白云，像是从车窗外拍摄。"
                       ]
        self.shorts = ["香港市区街道","维多利亚港","乘坐飞机和汽车"]
        self.photos = [[1,2,3,4],[5,6,7,8],[9,10,11,12]]
        self.evtCnt = len(self.events)

        # 每个事件的topic数目不得超过10!!!
        self.topics = [
            ["照片里的楼很高，其中有一张照片拍摄于傍晚，你站在国际金融中心大楼前。这个楼有上百层。当时在市区玩的印象如何?对这些高楼有什么印象?", 
             "照片既有白天，也有晚上。你们那天是在市区玩了一整天吗?都去了哪里?", 
             "3张照片是你的单人照，1张照片是你和另一个朋友的合影。照片中，你都穿着黄色连衣裙，朋友则穿着黑色T恤和黑底蓝红花色裙子。你还有印象吗?"
            ],
            ["照片中,维多利亚港对岸高楼林立,霓虹灯闪烁。水面上映出很亮的光。你对维多利亚港的印象如何，都玩了什么?",
             "照片中,有5位女士的合影。前排的一位坐着轮椅，后排的四位站着。你站在中间，穿着黄色连衣裙。你记得他们吗?"
            ],
            ["照片中,飞机上写着中国南方航空。这是你们的飞机吗?你对那段飞行有什么印象吗?",
             "照片中还有很美的云彩。蓝天上云朵密布。你是特地保留了这些云朵的照片吗",
             "后两张照片, 像是你从车内向窗外拍摄。车窗外还能看到路上密集的车辆。当时是堵车了吗? "
            ]
        ]
        
        self.isTopicTalked = []
        for eid in range(self.evtCnt):
            e_topicTalked = [False] * len(self.topics[eid])
            self.isTopicTalked.append(e_topicTalked)
        
    
    #
    #
    # ________________________ Helper Functions ________________________
    def call_llm(self, content, max_tokens = 200, model="gpt-4-vision-preview"):
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
        
    def save_chat_history(self, prefix):
        log_prefix = prefix + '_' + datetime.now().strftime("%Y%m%d")
        log_postfix = 0        
        with self.lock:
            for filename in os.listdir("./Reviver_Proactive/logs"):
                if filename.startswith(log_prefix):
                    log_postfix += 1
        log_path = "./Reviver_Proactive/logs/{}_{}.log".format(log_prefix, log_postfix)

        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(json.dumps({"chat_history":self.chat_history}, ensure_ascii=False, indent=4))
        print("本次聊天记录已保存至", log_path)

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

    # check whether the user has more questions
    def require_vqa(self, user_input):
        content = []
        task = "请判断用户输入中是否包含提问。用户输入是:{}。你的输出，请只输出Y或N。Y代表符合条件，N则反之。".format(user_input)
        content.append({"role": "user", "content": task})
        
        reply = self.call_llm(content)
        console_log("用户是否提问:{}".format(reply))

        return reply=="Y"
    
    def user_agree(self, user_input):
        content = []
        content.append(self.chat_history[-1])
        task = "请根据用户输入，判断用户是否同意。满足任一条件，都算用户同意:(1)用户说了积极的词语，比如'好的','嗯','没问题';(2)用户没有提问;(3)用户的问题是关于下一个场景的，比如:'还有什么?','下一个场景是什么?'。用户输入是:{}。你的输出，请只输出Y或N。Y代表用户同意，N则没有".format(user_input)
        content.append({"role": "user", "content": task})
        
        reply = self.call_llm(content)
        console_log("用户是否同意:{}".format(reply))

        return reply=="Y"
    
    def topic_to_discuss(self):
        candidates = ""
        topics = self.topics[self.curEid]
        talked = self.isTopicTalked[self.curEid]

        for i in range(len(talked)):
            if not talked[i]:
                candidates += str(i) + " " + topics[i] + "\n"
        return candidates
    
    def get_one_topic(self):
        topics = self.topics[self.curEid]
        talked = self.isTopicTalked[self.curEid]

        for i in range(len(talked)):
            if not talked[i]:
                return i
        return None
    
    def simple_reply_helper(self, user_input):
        content = []
        content.extend(self.chat_history[(-6 if len(self.chat_history)>=6 else 0):])

        task = "用户输入是:{}".format(user_input)

        # add photos
        photo_content = self.add_relevant_photo()
        content.append({"role": "user", "content": photo_content})
        task += "请你根据用户输入，找到照片中最相关的信息，简单明了地回答用户。注意:\
            (1) 你的回答必须忠于照片，不要想象照片外的内容。\
            (2) 你的回答必须是事实描述，请描述尽可能多的视觉信息，比如颜色和形状。不要带有主观判断。\
            (3) 请不要逐个描述每张照片。不要在回答中提到第X张照片. \
            (4) 请完全用陈述句,不要向用户提问。\
            (5) 不要超过100字。\
            "
        
        task += "以下是一些样例:\
            (1) 用户问: 我穿的什么衣服? 你的回答:你穿的是绿色连衣裙，上面有白色花纹。\
            (2) 用户说: 我只记得夜景很不错。 你的回答:照片中的夜景很漂亮，有林立的高楼，和五颜六色的灯光。\
            (3) 用户说: 我记得吃的很好，吃了很多餐厅。 你的回答:照片里没有看到食物。\
            "

        # 是否有问题? 有的话要回答问题。
        # if self.require_vqa(user_input):

        # else:
        #     task += "请按如下规则回复用户:(1)如果用户描述超过20个字，请回复: 你的描述很吸引人。(2)如果用户说记不太清了，请你回复:没关系。(3)其他情况，请回复: 谢谢你的分享。注意：请不要说任何其他内容!"
        
        return content, task

    #
    #
    # ________________________ Atomic Response Functions ________________________
    def event_intro(self):
        reply = self.events[self.curEid]
        reply += "我的描述准确吗?你记得当时在做什么吗?"

        return reply
    
    def event_discussion(self, user_input, candidate_topics = None):
        # first, request a simple reply
        content, task = self.simple_reply_helper(user_input)
        
        ## then, add a proactive strategy
        # task += "然后，请你从以下候选话题中，选择一个最能和你的回复连贯起来的话题。候选话题是:{}".format(candidate_topics)
        # task += "请以如下json格式输出:{\"id\":1,\"ans\":\"你的回答\"}"
        # content.append({"role": "user", "content": task})

        # raw_reply = self.call_llm(content)
        # reply_json = json_parser(raw_reply)

        content.append({"role": "user", "content": task})
        reply = self.call_llm(content)

        tid = self.get_one_topic()

        # 标记该话题已被讨论
        console_log("抛出新的话题，编号:{}".format(tid))
        reply += "另外，我注意到:" + self.topics[self.curEid][tid]
        self.isTopicTalked[self.curEid][tid] = True

        return reply
    
    def sug_summary(self, user_input):
        # first, request a simple reply
        content, task = self.simple_reply_helper(user_input)
        content.append({"role": "user", "content": task})
        reply = self.call_llm(content)

        # then, suggest generating a summary
        reply += "关于{}场景，你还有更多问题吗?没有的话, 我会为您生成一段文字回忆录。".format(self.shorts[self.curEid])
        self.suggSummary = True
        return reply
    
    def sug_next_event(self, user_input):
        # first, request a simple reply
        content, task = self.simple_reply_helper(user_input)
        content.append({"role": "user", "content": task})
        reply = self.call_llm(content)
        
        ## then, suggest moving on to the next event
        reply += "关于{}场景，你还有更多问题吗?没有的话, 我们可以聊下一个场景。".format(self.shorts[self.curEid])
        self.suggNextEvent = True

        return reply
    
    def generate_summary(self):
        content = []
        content.extend(self.chat_history)

        task = "请根据上述对话历史，为用户生成一段回忆录。请忠于对话历史的表述，不要想象对话之外的内容。请将回复控制在200个字以内。:"
        content.append({"role": "user", "content": task})
        
        reply = self.call_llm(content, max_tokens=500)

        return reply
    
    #
    #
    # ________________________ Mid-Level Functions ________________________

    def summary_or_not(self, user_input):
        # check whether the user has more questions
        agree = self.user_agree(user_input)

        # if the user has no further questions, then move on 
        if agree:
            console_log("生成回忆中")
            reply = self.generate_summary()
        # if the user has further questions, then reply
        else:
            reply = self.proactive_discussion(user_input)
        return reply
    
    def next_event_or_not(self, user_input):
        # check whether the user has more questions
        agree = self.user_agree(user_input)

        # if the user has no further questions, then move on 
        if agree:
            self.curEid = self.curEid + 1
            reply = self.event_intro()
        # if the user has further questions, then reply
        else:
            reply = self.proactive_discussion(user_input)
        return reply
    
    def proactive_discussion(self, user_input):
        # candidate_topics = self.topic_to_discuss()
        # console_log("备选话题:{}".format(candidate_topics))

        # if all the topics of the current event has been discussed, then suggest moving on
        if self.get_one_topic() is None:
            # if no more topics, then suggest generating a summary
            if self.curEid == self.evtCnt - 1:
                reply = self.sug_summary(user_input)
            # if there is at least one new topic, then suggest moving on to the next topic
            else:
                reply = self.sug_next_event(user_input)
        # if there are some topics left, then bring up new topics
        else:
            reply = self.event_discussion(user_input)

        return reply

    #
    #
    # ________________________ Response Functions ________________________
    def introduction(self):
        reply = self.superE + "我们从第一个场景开始聊吧!"
        self.chat_history.append({"role": "assistant", "content": reply})

        return reply
    
    def first_event_intro(self, user_input):
        reply = self.event_intro()
        
        self.chat_history.append({"role": "user", "content": user_input})
        self.chat_history.append({"role": "assistant", "content": reply})

        return reply
    
    def chat(self, user_input):

        # check whether the agent should generate a summary
        if self.suggSummary:
            self.suggSummary = False
            reply = self.summary_or_not(user_input)

        # check whether the agent should move on to the next event
        elif self.suggNextEvent:
            self.suggNextEvent = False
            reply = self.next_event_or_not(user_input)
        
        # check the proactive strategy
        else:
            reply = self.proactive_discussion(user_input)

        self.chat_history.append({"role": "user", "content": user_input})
        self.chat_history.append({"role": "assistant", "content": reply})

        return reply