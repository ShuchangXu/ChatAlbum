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

def human_check_reply(llm_reply, reply_type):
    print("\n【实验后台】Human Check LLM's {}:".format(reply_type), llm_reply)
    admin_input = input("【实验后台】Press \"Enter\" to accept, otherwise please input a corrected {}:".format(reply_type))
    reply = llm_reply
    
    while True:
        if admin_input == "":
            if reply == llm_reply:
                print("【实验后台】LLM's {} is accepted.".format(reply_type))
                return None
            else:
                print("【实验后台】Corrected {} is accepted.".format(reply_type))
                return reply
        else:
            reply = admin_input
            print("【实验后台】Corrected {}:".format(reply_type), reply)
            admin_input = input("【实验后台】Press \"Enter\" to accept, otherwise please input a new corrected {}:".format(reply_type))
        
        

class eType(Enum):
    NONE = 'N'
    NEXT = 'E'
    PREV = 'P'

class ReviverPro:
    #
    #
    # ________________________ Initialization ________________________
    def __init__(self, api_key, user="dev0214", resume=None):
        if not resume:
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
            self.original_eid = None
            self.corrected_eid = None

            self.switchingEvent = True
            self.wandering = False
            self.forwardProgress = 0 # last event during recall

            self.sumPending = False
            self.evtPending = False
            self.wanPending = False
            self.hasSuggested = False

            self.isEventTalked = None
            self.isTopicTalked = None

            self.ended = False

            # Chat History
            self.chat_history = []
            self.dialogue_turn = -1 # then it will be 0 for introduction

            # ________ User Info ________
            self.user = user            
            self.photo_dir = os.path.join(SCRIPT_DIR, "photos", self.user)
            self.json_dir = os.path.join(SCRIPT_DIR, "mtree_json", self.user)
            
            # ________ Initialize Mtree _______
            self.init_mtree()
            
            #________ Log Content ________
            self.log = {
                "user": self.user,
                "resume": None,
                "datetime": datetime.now().strftime("%Y-%m-%d-%H:%M"),
                "photo_dir": self.photo_dir,
                "mtree": {                    
                    "superE": self.superE,
                    "events": self.events,
                    "evtCnt": self.evtCnt,
                    "evtStr": self.evtStr,
                    "shorts": self.shorts,
                    "photos": self.photos,
                    "topics": self.topics
                },
                
                "reply_history": [],
                "state_history": [],
            }
            
        
        else:
            self.log = json.loads(open(os.path.join(SCRIPT_DIR, "logs", resume), 'r', encoding='utf-8').read())
            
            self.user = self.log["user"]
            self.photo_dir = self.log["photo_dir"]
            
            self.superE = self.log["mtree"]["superE"]
            self.events = self.log["mtree"]["events"]
            self.evtCnt = self.log["mtree"]["evtCnt"]
            self.evtStr = self.log["mtree"]["evtStr"]
            self.shorts = self.log["mtree"]["shorts"]
            self.photos = self.log["mtree"]["photos"]
            self.topics = self.log["mtree"]["topics"]
            
            self.reply_history = self.log["reply_history"]
            self.state_history = self.log["state_history"]
            self.chat_history = self.log["chat_history"]
            
            latest_state_history = self.state_history[-1]
                        
            self.dialogue_turn = latest_state_history["dialogue_turn"]
            
            self.original_eid = latest_state_history["original_eid"]
            self.corrected_eid = latest_state_history["corrected_eid"]
            
            self.curEid = latest_state_history["curEid"]
            self.switchingEvent = latest_state_history["switchingEvent"]
            
            self.wandering = latest_state_history["wandering"]
            self.forwardProgress = latest_state_history["forwardProgress"]
            
            self.sumPending = latest_state_history["sumPending"]
            self.evtPending = latest_state_history["evtPending"]
            self.wanPending = latest_state_history["wanPending"]
            
            self.hasSuggested = latest_state_history["hasSuggested"]
            
            self.isEventTalked = latest_state_history["isEventTalked"]
            self.isTopicTalked = latest_state_history["isTopicTalked"]
            
            self.ended = latest_state_history["ended"]     
            
            self.log["datetime"] = datetime.now().strftime("%Y-%m-%d-%H:%M"),
            self.log["resume"] = resume              
        
        
        # ________ OpenAI client ________
        self.client = OpenAI(api_key=api_key, timeout=TIME_OUT)
        
        self.lock = threading.Lock()
        
        # ______ Log Path _______
        log_prefix = self.user + '_' + datetime.now().strftime("%Y%m%d")
        log_postfix = 0        
        with self.lock:
            for filename in os.listdir("./Reviver_Proactive/logs"):
                if filename.startswith(log_prefix):
                    log_postfix += 1
        self.log_path = "./Reviver_Proactive/logs/{}_{}.log".format(log_prefix, log_postfix)
        with open(self.log_path, 'w', encoding='utf-8') as f:
            f.write(" ")
        
    
    def init_mtree(self):        
        json_path = os.path.join(self.json_dir, "memory_tree.json")
        mtree_json = json.loads(open(json_path, 'r', encoding='utf-8').read())

        self.superE = mtree_json["super_event"]
        self.events = mtree_json["events"]
        self.evtCnt = len(self.events)
        self.evtStr = mtree_json["evtStr"]
        self.shorts = mtree_json["shorts"]
        self.photos = mtree_json["photos"]
        self.topics = mtree_json["topics"]
        
        
        self.isEventTalked = []
        self.isTopicTalked = []
        for eid in range(self.evtCnt):
            self.isEventTalked.append(False)

            e_topicTalked = [False for _ in range(len(self.topics[eid]))]
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

        # reply="\ncalling LLM:{}\n".format(content)
        return reply
    
    def encode_image(self, image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
        
    def record_current_dialogue_turn(self, user_input, original_reply, corrected_reply):
        self.dialogue_turn += 1
        self.log["reply_history"].append({
            "dialogue_turn": self.dialogue_turn,
            "user_input": user_input,
            "original_reply": original_reply,
            "corrected_reply": corrected_reply
        })
        
        self.log["state_history"].append({
            "dialogue_turn": self.dialogue_turn,
            "original_eid": self.original_eid,
            "corrected_eid": self.corrected_eid,
            
            "curEid": self.curEid,
            "switchingEvent": self.switchingEvent,
            
            "wandering": self.wandering,
            "forwardProgress": self.forwardProgress,

            "sumPending": self.sumPending,
            "evtPending": self.evtPending,
            "wanPending": self.wanPending,
            "hasSuggested": self.hasSuggested,

            "isEventTalked": self.isEventTalked,
            "isTopicTalked": self.isTopicTalked,

            "ended": self.ended
        })
        
        if (self.dialogue_turn % 3) == 0 and self.dialogue_turn > 0:
            self.save_chat_history(self.log_path+".{}".format(self.dialogue_turn))
        
    def save_chat_history(self, log_path=None): 
        if not log_path:
            log_path = self.log_path
              
        self.log["chat_history"] = self.chat_history
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(json.dumps(self.log, ensure_ascii=False, indent=4))
        print("最新聊天记录已保存至", log_path)

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
        task = "请根据用户输入，判断用户是否同意。满足任一条件，都算用户同意:\
            (1)用户说了积极的词语，比如'好的','嗯','没问题';\
            (2)用户没有提问;\
            (3)用户的问题是关于下一个场景的，比如:'还有什么?','下一个场景是什么?'。\
            用户输入是:{}。你的输出，请只输出Y或N。Y代表用户同意，N则没有".format(user_input)
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
        task += "请你按如下步骤思考:\
            (第一步) 根据对话历史和用户输入，判断用户想了解的是什么内容。\
            (第二步) 请你找到照片中最相关的内容，简洁地回答用户。\
            "
        task += "请你按如下格式组织回答:\
            关于(用户关心的内容),\
            照片里(你从照片里看到的信息)\
            "
        
        task += "以下是一些样例:\
            (1) 用户问: 我穿的什么衣服? 你的回答:关于你穿的衣服, 照片里显示，你穿的是绿色连衣裙，上面有白色花纹。\
            (2) 用户说: 我只记得夜景很不错。你的回答:关于夜景, 照片中的高楼灯火通明，灯光也是五颜六色的。\
            (3) 用户说: 我记得吃的很好，吃了很多餐厅。 你的回答:关于你提到的餐厅，照片里没有看到食物或餐厅。\
            "
        
        task += "在回答中,请务必注意:\
            (1) 你的回答必须忠于照片，不要想象照片外的内容。\
            (2) 你的回答必须是事实描述，请描述尽可能多的视觉信息，比如颜色和形状。不要带有主观判断。\
            (3) 请不要逐个描述每张照片。不要在回答中提到第X张照片. \
            (4) 请完全用陈述句,不要向用户提问。\
            (5) 不要超过100字。\
            "
        # 是否有问题? 有的话要回答问题。
        # if self.require_vqa(user_input):

        # else:
        #     task += "请按如下规则回复用户:(1)如果用户描述超过20个字，请回复: 你的描述很吸引人。(2)如果用户说记不太清了，请你回复:没关系。(3)其他情况，请回复: 谢谢你的分享。注意：请不要说任何其他内容!"
        
        return content, task
    
    #
    #
    # ________________________ Suggesting next events ________________________
    def sug_summary(self, user_input):
        # first, request a simple reply
        content, task = self.simple_reply_helper(user_input)
        content.append({"role": "user", "content": task})
        reply = self.call_llm(content)

        # then, suggest generating a summary
        reply += "关于{}场景，你还有更多问题吗?没有的话, 我会为您生成一段文字回忆录。".format(self.shorts[self.curEid])
        self.sumPending = True
        self.hasSuggested = True
        return reply
    
    def sug_next_event(self, user_input):
        # first, request a simple reply
        content, task = self.simple_reply_helper(user_input)
        content.append({"role": "user", "content": task})
        reply = self.call_llm(content)
        
        ## then, suggest moving on to the next event
        reply += "关于{}场景，你还有更多问题吗?没有的话, 我们可以聊下一个场景:{}。".format(self.shorts[self.curEid], self.shorts[self.curEid + 1])
        self.evtPending = True
        self.hasSuggested = True

        return reply
    
    def sug_end_wander(self, user_input):
        # first, request a simple reply
        content, task = self.simple_reply_helper(user_input)
        content.append({"role": "user", "content": task})
        reply = self.call_llm(content)

        ## then, suggest go back to the non-wander event
        reply += "关于{}场景，你还有更多问题吗?没有的话, 我们可以回到刚才在聊的场景:{}。".format(self.shorts[self.curEid], self.shorts[self.forwardProgress])
        self.wanPending = True
        self.hasSuggested = True

        return reply
    
    def summary_or_not(self, user_input):
        # check whether the user has more questions
        agree = self.user_agree(user_input)

        # if the user has no further questions, then move on 
        if agree:
            self.hasSuggested = False
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
            self.switchingEvent=True
            self.curEid += 1
            self.forwardProgress = self.curEid
            self.hasSuggested = False
            reply = self.proactive_discussion(user_input)
        # if the user has further questions, then reply
        else:
            reply = self.proactive_discussion(user_input)
        return reply
    
    def end_wander_or_not(self, user_input):
        # check whether the user has more questions
        agree = self.user_agree(user_input)

        # if the user has no further questions, then move on 
        if agree:
            self.switchingEvent=True
            self.curEid = self.forwardProgress
            self.wandering = False
            self.hasSuggested = False
            reply = self.proactive_discussion(user_input)
        # if the user has further questions, then reply
        else:
            reply = self.proactive_discussion(user_input)
        return reply
    
    #
    #
    # ________________________ Mid-Level Functions ________________________
    def event_intro(self, user_input):
        # first, request a simple reply
        content, task = self.simple_reply_helper(user_input)
        content.append({"role": "user", "content": task})
        reply = self.call_llm(content)
        
        reply += "因为这是第一次聊{},我整体介绍下这个场景.".format(self.shorts[self.curEid])
        reply += self.events[self.curEid]
        reply += "我的描述准确吗?你记得当时在做什么吗?"

        self.isEventTalked[self.curEid] = True

        return reply
    
    def sug_new_topic(self, user_input, candidate_topics = None):
        # first, request a simple reply
        content, task = self.simple_reply_helper(user_input)
        content.append({"role": "user", "content": task})
        reply = self.call_llm(content)

        ## then, add a proactive strategy
        # task += "然后，请你从以下候选话题中，选择一个最能和你的回复连贯起来的话题。候选话题是:{}".format(candidate_topics)
        # task += "请以如下json格式输出:{\"id\":1,\"ans\":\"你的回答\"}"
        # content.append({"role": "user", "content": task})

        # raw_reply = self.call_llm(content)
        # reply_json = json_parser(raw_reply)

        tid = self.get_one_topic()

        # 标记该话题已被讨论
        console_log("抛出新的话题，编号:{}".format(tid))
        reply += "另外，我注意到:" + self.topics[self.curEid][tid]
        self.isTopicTalked[self.curEid][tid] = True

        return reply
    
    def proactive_discussion(self, user_input):
        # candidate_topics = self.topic_to_discuss()
        # console_log("备选话题:{}".format(candidate_topics))
        
        reply = ""
        if self.switchingEvent:
            reply = "我们来聊关于{}的场景。".format(self.shorts[self.curEid])

        if self.isEventTalked[self.curEid] == False:# if first time talk, event intro
            reply += self.event_intro(user_input)
        
        elif self.get_one_topic() is not None:# if there are some topics left, then bring up new topics
            reply += self.sug_new_topic(user_input)
        
        else:# if all the topics of the current event has been discussed, then suggest moving on
            if self.wandering:# if wandering, then go back
                reply += self.sug_end_wander(user_input)
            
            elif self.curEid == self.evtCnt - 1:# if no more topics, then suggest generating a summary
                reply += self.sug_summary(user_input)
            
            else:# if there is at least one new topic, then suggest moving on to the next topic
                reply += self.sug_next_event(user_input)

        return reply

    def event_selector(self, user_input):
        content = []
        task = "你的任务是，根据用户输入，判断用户是否想谈论某一话题。用户输入是:{}。全部话题列表是:{}。每个话题编号后列出了对应的关键词。\n".format(user_input, self.evtStr)
        task += "请按照如下步骤思考,并直接输出字母或数字编号.不要输出其他任何内容.\
            (1) 用户是否表达想聊其他/下一个话题?类似表述有:'其他的','下一个','别的','还有什么?'等.如有,请直接输出E.反之继续思考。\
            (2) 用户是否表达想回到上一个话题?类似表述有:'回到上一个话题','刚刚聊的是什么?'等.如有,请直接输出P.反之继续思考。\
            (3) 用户是否提及了话题{}相关信息?如是,请直接输出数字{}。反之继续思考\
            (4) 如果用户有明确提及想了解的内容,比如:'我的照片里有XX(公园合影)吗?'，'我们来聊聊XX(小猫)吧'，请根据用户提到的关键词XX，寻找最相关的话题,并输出话题的编号。\
                如果没有，请直接输出N。\n".format(str(self.curEid),str(self.curEid))
        task += "以下是一些示例。示例所使用的话题列表是:\
            1 市区街道,高楼; 2 公园,草坪,狗; n3 喷泉\
            (1) 用户输入: 我记得楼特别的高 输出:N 原因: 用户没有明确提及想了解的内容\
            (2) 用户输入: 我的照片里有动物吗? 输出:2 原因: 话题2的关键词有狗，和用户的问题高度相关\
            (3) 用户输入: 还有其他的照片吗? 输出:E 原因: 用户明确表达想聊其他话题\
            (4) 用户输入: 我们回到上一个话题吧。 输出: P 原因: 用户明确表达想聊上一个话题\
            "
        content.append({"role": "user", "content": task})
        
        reply = self.call_llm(content)

        eid = eType.NONE
        if reply == "E":
            eid = eType.NEXT
        elif reply == "P":
            eid = eType.PREV
        elif reply == "N":
            eid = eType.NONE
        else:
            eid = int(reply)
        console_log("相关事件:{}".format(eid))
        self.original_eid = reply
        
        corrected_eid = human_check_reply(reply, "event prediction")
        self.corrected_eid = corrected_eid
        
        if corrected_eid == "E":
            corrected_eid = eType.NEXT
        elif corrected_eid == "P":
            corrected_eid = eType.PREV
        elif corrected_eid == "N":
            corrected_eid = eType.NONE
        elif corrected_eid is not None:
            corrected_eid = int(reply)
            
        eid = corrected_eid if corrected_eid else eid
        if corrected_eid:
            console_log("修改后相关事件:{}".format(eid))

        return eid

    #
    #
    # ________________________ Response Functions ________________________
    def introduction(self):
        reply = self.superE + "我们先聊第一个场景吧!第一个场景是{}!".format(self.shorts[self.curEid])
        self.chat_history.append({"role": "assistant", "content": reply})
        self.record_current_dialogue_turn(None, reply, None)
        return reply
    
    def generate_summary(self):
        content = []
        content.extend(self.chat_history)

        task = "请根据上述对话历史，为用户生成一段回忆录。请忠于对话历史的表述，不要想象对话之外的内容。请将回复控制在200个字以内。:"
        content.append({"role": "user", "content": task})
        
        reply = self.call_llm(content, max_tokens=500)

        self.ended = True

        return reply

    
    def chat(self, user_input):
        self.original_eid, self.corrected_eid = None, None
        # check whether the user agrees to generate a summary
        if self.sumPending:
            self.sumPending = False
            reply = self.summary_or_not(user_input)

        # check whether the user agrees to move on to the next event
        elif self.evtPending:
            self.evtPending = False
            reply = self.next_event_or_not(user_input)

        # check whether the user agrees to end wandering
        elif self.wanPending:
            self.wanPending = False
            reply = self.end_wander_or_not(user_input)
        
        else:
            # determine the event
            eid = self.event_selector(user_input)

            if eid == eType.NONE or eid == self.curEid: 
                # do not change the current event when:
                # eid == eType.NONE "未明确指定事件"
                # eid == self.curEid "指定当前场景"
                self.switchingEvent = False
            else:
                self.switchingEvent = True
                self.hasSuggested = False

                if self.wandering:
                    if eid == eType.NEXT or eid == eType.PREV or eid == self.forwardProgress:
                        # go back to forward recall when:
                        # eid == eType.NEXT "下一个，别的，继续，其他的，还有什么"
                        # eid == eType.PREV "之前的"
                        # eid == self.forwardProgress "指定线性叙事的中断场景"
                        self.wandering = False
                        self.curEid = self.forwardProgress
                    else:
                        # jump to a specified event when:
                        # eid is a number, and eid not in (self.forwardProgress, self.curEid)
                        self.curEid = eid

                else:
                    if (eid == eType.NEXT and self.curEid < self.evtCnt - 1) or eid == self.curEid + 1:
                        # move on to the next event when:
                        # eid == eType.NEXT "下一个，别的，继续，其他的，还有什么"
                        # eid == self.curEid + 1
                        self.curEid += 1
                        self.forwardProgress = self.curEid

                    elif (eid == eType.NEXT and self.curEid == self.evtCnt - 1):
                        reply = "所有照片都有过讨论了, 我为您生成了一段回忆录:" + self.generate_summary()
                                                
                        corrected_reply = human_check_reply(reply, "reply") # None if original reply is accepted
                        self.record_current_dialogue_turn(user_input, reply, corrected_reply)
                        
                        reply = corrected_reply if corrected_reply else reply                        
                        self.chat_history.append({"role": "user", "content": user_input})
                        self.chat_history.append({"role": "assistant", "content": reply})
                        return reply

                    elif eid == eType.PREV:
                        # jump back
                        self.wandering = True
                        self.curEid -= 1
                    
                    else:
                        # 
                        self.wandering = True
                        self.curEid = eid

        
        reply = self.proactive_discussion(user_input)
                              
        corrected_reply = human_check_reply(reply, "reply") # None if original reply is accepted
        self.record_current_dialogue_turn(user_input, reply, corrected_reply)
        
        reply = corrected_reply if corrected_reply else reply 
        self.chat_history.append({"role": "user", "content": user_input})
        self.chat_history.append({"role": "assistant", "content": reply})

        return reply