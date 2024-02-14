import os
import threading
from openai import OpenAI
from datetime import datetime

TIME_OUT = 30

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
        # self.photos = None
        
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
    
    def init_mtree(self):
        self.superE = "这是19年6月底,你在香港和广州拍摄的照片，一共有11张。其中有你在香港市区的拍照留念，有你在维多利亚港和朋友的合影，还有飞机和蓝天白云的照片。"
        self.events = ["第一个场景,是你在香港市区街道上的拍照留念，一共有4张照片。你穿着一条黄色连衣裙，在香港很多高楼前面拍照。看起来像是你在市区游玩。",
                       "第二个场景,是你在维多利亚港和朋友们的合影，一共有4张照片。既有夜景海港，对面霓虹灯闪烁；又有白天的海港。",
                       "第三个场景,是乘坐飞机和汽车的照片，一共有4张。前两张是拍摄的飞机，似乎是在候机大厅。后两张拍摄的蓝天白云，像是从车窗外拍摄。"
                       ]
        self.evtCnt = len(self.events)

        # 每个事件的topic数目不得超过10!!!
        self.topics = [
            ["这些楼很高，其中有一张照片拍摄于傍晚，你站在国际金融中心大楼前。这个楼有上百层。当时在市区玩的印象如何?对这些高楼有什么印象?", 
             "照片既有白天，也有晚上。你们那天是在市区玩了一整天吗?都去了哪里?", 
             "3张照片是你的单人照，1张照片是你和另一个朋友的合影。照片中，你都穿着黄色连衣裙，朋友则穿着黑色T恤和黑底蓝红花色裙子。你还有印象吗?"
            ],
            ["夜景中,维多利亚港对岸高楼林立,,霓虹灯闪烁。水面上映出很亮的光。你对维多利亚港是什么印象，都玩了什么?",
             "照片里，有5位女士的合影。前排的一位坐着轮椅，后排的四位站着。你站在中间，穿着黄色连衣裙。你记得他们吗?"
            ],
            ["飞机上写着中国南方航空。这是你们的飞机吗?你对那段飞行有什么印象吗?",
             "后两张照片, 像是你从车内向窗外拍摄。蓝天上云朵密布，车窗外还能看到路上密集的车辆。当时是堵车了吗? 云朵感受如何?"
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
    
    # check whether the user has more questions
    def has_question(self, user_input):
        content = []
        task = "请根据用户输入，判断用户是否有明确的问题。用户输入是:{}。你的输出，请只输出Y或N。Y代表用户有明确问题，N则没有".format(user_input)
        content.append({"role": "user", "content": task})
        
        reply = self.call_llm(content)
        return reply=="Y"
    
    def user_agree(self, user_input):
        content = []
        content.append(self.chat_history[-1])
        task = "请根据用户输入，判断用户是否同意(比如:好的,嗯,没问题)。用户输入是:{}。你的输出，请只输出Y或N。Y代表用户同意，N则没有".format(user_input)
        content.append({"role": "user", "content": task})
        
        reply = self.call_llm(content)
        return reply=="Y"
    
    def topic_to_discuss(self):
        candidates = ""
        topics = self.topics[self.curEid]
        talked = self.isTopicTalked[self.curEid]

        for i in range(len(talked)):
            if not talked[i]:
                candidates += str(i) + " " + topics[i] + "\n"
        return candidates
    
    def save_chat_history(self, prefix):
        log_prefix = prefix + '_' + datetime.now().strftime("%Y%m%d")
        log_postfix = 0        
        with self.lock:
            for filename in os.listdir("./Reviver_Proactive/logs"):
                if filename.startswith(log_prefix):
                    log_postfix += 1
        log_path = "./logs/{}_{}.log".format(log_prefix, log_postfix)

        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(self.chat_history)
        print("本次聊天记录已保存至", log_path)

    def simple_reply_helper(self, user_input):
        content = []
        content.extend(self.chat_history[(-6 if len(self.chat_history)>=6 else 0):])

        task = "用户输入是:{}".format(user_input)

        # 是否有问题? 有的话要回答问题。
        if self.has_question(user_input):
            # add photos
            task += "请你回答用户输入的问题。"
        else:
            task += "请你先简单回复用户(不超过10个字),例如:确实;好棒;没关系;你的描述很引人入胜。"
        
        return content, task

    #
    #
    # ________________________ Atomic Response Functions ________________________
    def event_intro(self):
        content = []
        content.extend(self.chat_history[(-6 if len(self.chat_history)>=6 else 0):])

        print("(log)当前事件编号:{}".format(self.curEid))
        task = "请首先向用户介绍这个事件。事件描述如下:{}。你的介绍必须和这段描述完全一致，不要想象其他信息。".format(self.events[self.curEid])
        task += "然后，请你询问用户:我的描述准确吗?你记忆中是什么样的?"
        content.append({"role": "user", "content": task})
        
        reply = self.call_llm(content)

        return reply
    
    def event_discussion(self, user_input, candidate_topics = None):
        # first, request a simple reply
        content, task = self.simple_reply_helper(user_input)
        
        ## then, add a proactive strategy
        ## TODO: 兼容10个或更多topics!
        task += "然后，请你自然地转移到下一个话题。请从以下候选话题中，选择一个最能和当前对话连贯起来的，并完全忠于这个话题描述回复用户。候选话题是:{}".format(candidate_topics)
        task += "请按如下格式输入:首先，请直接输出你选择的候选话题编号(1位数字)，不要带任何前缀! 然后直接输入你对用户的回答。回答中，既要包括对用户的回复，还要包括自然转入下一个话题。"
        task += "输出样例:1确实像你说的那样。我还在照片里看到XX"
        content.append({"role": "user", "content": task})

        reply = self.call_llm(content)

        # 标记该话题已被讨论
        tid = int(reply[0])
        self.isTopicTalked[self.curEid][tid] = True
        print("(log)当前话题编号:{}".format(tid))

        reply = reply[1:]

        return reply
    
    def sug_summary(self, user_input):
        # first, request a simple reply
        content, task = self.simple_reply_helper(user_input)
        
        ## then, add a proactive strategy
        task += "然后，请你自然地询问用户，是否要生成一段回忆录。参考回复是:关于当前的XX场景，你还有更多问题吗?没有的话, 我会为您生成一段文字回忆录。"
        content.append({"role": "user", "content": task})

        ## get a reply
        reply = self.call_llm(content)
        return reply
    
    def sug_next_event(self, user_input):
        # first, request a simple reply
        content, task = self.simple_reply_helper(user_input)
        
        ## then, add a proactive strategy
        task += "然后，请你自然地询问用户，是否要讨论下一个场景。下一个场景是:{}。参考回复是:关于当前的XX场景，你还有更多问题吗?没有的话, 我们可以聊下一个YY场景。".format(self.events[self.curEid+1])
        content.append({"role": "user", "content": task})

        ## get a reply
        reply = self.call_llm(content)
        return reply
    
    def generate_summary(self):
        content = []
        content.extend(self.chat_history)

        task = "请根据上述对话历史，为用户生成一段回忆录。请控制在200个字以内。:"
        content.append({"role": "user", "content": task})
        
        reply = self.call_llm(content)
        return reply

    def summary_or_not(self, user_input):
        # check whether the user has more questions
        agree = self.user_agree(user_input)

        # if the user has no further questions, then move on 
        if agree:
            reply = self.generate_summary()
        # if the user has further questions, then reply
        else:
            reply = self.event_discussion(user_input)
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
        if self.suggNextEvent:
            self.suggNextEvent = False
            reply = self.next_event_or_not(user_input)
        
        # check the proactive strategy
        else:
            candidate_topics = self.topic_to_discuss()

            # if all the topics of the current event has been discussed, then suggest moving on
            if candidate_topics == "":
                # if no more topics, then suggest generating a summary
                if self.curEid == self.evtCnt - 1:
                    reply = self.sug_summary(user_input)
                    self.suggSummary = True
                # if there is at least one new topic, then suggest moving on to the next topic
                else:
                    reply = self.sug_next_event(user_input)
                    self.suggNextEvent = True
            
            # if there are some topics left, then bring up new topics
            else:
                reply = self.event_discussion(user_input, candidate_topics)

        self.chat_history.append({"role": "user", "content": user_input})
        self.chat_history.append({"role": "assistant", "content": reply})

        return reply