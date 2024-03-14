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
    print("【console】:\n" + log)

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
        return None
    else:
        print("【实验后台】Corrected {} is accepted.".format(reply_type))
        return admin_input
        

class eType(Enum):
    NONE = 'N'
    NEXT = 'E'
    PREV = 'P'
    OVERVIEW = 'O'
    SUMMARY = 'S'

class ReviverPro:
    #
    #
    # ________________________ Initialization ________________________
    def __init__(self, api_key, user, resume=None):
        if not resume:
            # ________ This is the Memory Tree ________
            # Photo Information
            self.superE = None #"18年秋天，在青岛拍摄，一共有25张照片。其中有XXX，XXX等场景。"
            self.evtCnt = 0 # number of events
            self.events = None
            self.shorts = None
            self.metas = None
            self.topics = None
            self.photos = None
            
            # User Narrations
            self.event_narrations = None

            # ________ These variables tracked the progress ________
            self.curEid = 0
            self.commandEid = None
            # self.original_eid = None
            # self.corrected_eid = None

            self.wandering = False
            self.forwardProgress = 0 # last event during recall

            self.isEventTalked = None
            self.isTopicTalked = None

            self.summarizing = False
            self.overviewing = False

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
                "chat_history": [],
                "mtree": {                    
                    "superE": self.superE,
                    "events": self.events,
                    "evtCnt": self.evtCnt,
                    "evtStr": self.evtStr,
                    "shorts": self.shorts,
                    "metas": self.metas,
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
            self.metas = self.log["mtree"]["metas"]
            self.shorts = self.log["mtree"]["shorts"]
            self.photos = self.log["mtree"]["photos"]
            self.topics = self.log["mtree"]["topics"]
            
            self.reply_history = self.log["reply_history"]
            self.state_history = self.log["state_history"]
            self.chat_history = self.log["chat_history"]
            
            latest_state_history = self.state_history[-1]
                        
            self.dialogue_turn = latest_state_history["dialogue_turn"]
            
            self.curEid = latest_state_history["curEid"]
            self.commandEid = latest_state_history["commandEid"]
            
            self.wandering = latest_state_history["wandering"]
            self.forwardProgress = latest_state_history["forwardProgress"]
            
            self.isEventTalked = latest_state_history["isEventTalked"]
            self.isTopicTalked = latest_state_history["isTopicTalked"]

            self.summarizing = latest_state_history["summarizing"]
            self.overviewing = latest_state_history["overviewing"]

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
        self.metas = mtree_json["metas"]
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
        attempt_times = 3
        attempt_count = 0
        
        while attempt_count < attempt_times:
            attempt_count += 1
            try:                
                response = self.client.chat.completions.create(
                    messages = content,
                    model = model,
                    max_tokens = max_tokens
                )
                reply = response.choices[0].message.content
                return reply
            except Exception as e:
                print(e)
                if attempt_count < attempt_times:
                    input("Error occurs! Please press \"Enter\" to retry ({}/{}):".format(attempt_count, attempt_times))
                else:                
                    print("Error occurs! Program will exit ({}/{}).".format(attempt_count, attempt_times))
        exit()
    
    def encode_image(self, image_path):
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
        
    def record_current_dialogue_turn(self, user_input, original_reply, corrected_reply):
        self.dialogue_turn += 1
        self.log["reply_history"].append({
            "dialogue_turn": self.dialogue_turn,
            "user_input": user_input,
            "command_eid": self.commandEid,
            "original_reply": original_reply,
            "corrected_reply": corrected_reply
        })
        
        self.log["state_history"].append({
            "dialogue_turn": self.dialogue_turn,
            
            "curEid": self.curEid,
            "commandEid": self.commandEid,
            
            "wandering": self.wandering,
            "forwardProgress": self.forwardProgress,

            "isEventTalked": self.isEventTalked,
            "isTopicTalked": self.isTopicTalked,

            "summarizing": self.summarizing,
            "overviewing": self.overviewing
        })
        
        if (self.dialogue_turn % 3) == 0 and self.dialogue_turn > 0:
            self.save_chat_history(self.log_path)
        
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
    
    #
    #
    # ________________________ Replier ________________________

    def replier(self, user_input):
        vqa_or_not = input("Y for VQA:\n").replace(" ", "")
        if vqa_or_not not in ("Y", "y"):
            return ""
        content = []
        content.extend(self.chat_history[(-6 if len(self.chat_history)>=6 else 0):])

        task = "用户输入是:{}".format(user_input)

        # add photos
        photo_content = self.add_relevant_photo()
        content.append({"role": "user", "content": photo_content})
        task += "请根据对话历史和用户输入判断用户处于以下哪一种情况（无需输出判断序号），并作出对应回复：\
            （A）若用户提出问题，请根据用户的问题，寻找到照片中最相关的内容，简洁明了地回答。\
            （B）若用户谈及新的信息（地点、人、物等），则请根据用户提及的新信息，寻找到照片中最相关的内容，简洁明了地回答，\
                并且回答由两部分组成：你提到了(用户想了解的内容) + 我在照片里看到/没有看到(你从照片里看到的内容)。\
            "

        task += "请务必注意:\
            (1) 你的回答内容必须忠于照片，不要想象照片以外的内容。\
            (2) 你的描述用语必须客观，禁止任何带有主观判断的形容。\
            (3) 请描述尽可能多的视觉信息，比如颜色和形状，尽可能为视障用户勾勒出整幅图景。\
            (4) 请不要逐个描述每张照片。不要在回答中提到第X张照片。 \
            (5) 请完全用陈述句,不要向用户提问。\
            (6) 不要超过100字。\
            "
        content.append({"role": "user", "content": task})
        reply = self.call_llm(content)
        return reply
    
    #
    #
    # ________________________ Inspirer ________________________
        
    def event_intro(self):
        reply = "您照片中的第{}个场景是{}。".format(str(self.curEid+1), self.shorts[self.curEid])
        reply += self.events[self.curEid]

        return reply

    def topic_to_discuss(self):
        candidates = ""
        topics = self.topics[self.curEid]
        talked = self.isTopicTalked[self.curEid]

        for i in range(len(talked)):
            if not talked[i]:
                candidates += str(i) + " 此外，我注意到:" + topics[i] +"\n"
        return candidates
    
    def sug_next(self):
        done, todo, next = self.discuss_progress()
        if self.wandering:# if wandering, then go back
            inspiration = "{}场景中的主要信息都聊完了。要不要换个呢?刚刚还没聊场景是:{}。".format(self.shorts[self.curEid], next)
        
        elif next == "":# if no more topics, then suggest generating a summary
            inspiration = "这组照片的内容都聊过了。{}。你还有更多问题吗?没有的话, 我会为您生成一段文字回忆录。".format(done)
        
        else:# if there is at least one new topic, then suggest moving on to the next topic
            inspiration = "{}场景中的主要信息都聊完了。要不要聊下一个呢?下一个场景是:{}。".format(self.shorts[self.curEid], next)
        
        return inspiration

    def inspirer(self):
        intro = self.event_intro()
        nextE = self.sug_next()

        candidates = ""
        candidates += "I " + intro + "\n"
        candidates += self.topic_to_discuss()
        candidates += "E " + nextE + "\n"
        
        # console_log("Inspiration Candidates:\n"+candidates)
        # tid_str = input("tid:").replace(" ", "")

        # inspiration = ""
        # if tid_str.isdigit():
        #     tid = int(tid_str)
        #     inspiration = "从照片中，我还注意到:" + self.topics[self.curEid][tid]
        #     self.isTopicTalked[self.curEid][tid] = True
        # elif tid_str in ("I", 'i'):
        #     inspiration = intro
        # elif tid_str in ("E", 'e'):
        #     inspiration = nextE
        # else:
        #     pass
        
        return candidates
    
    #
    #
    # ________________________ State Transition ________________________

    def event_selector(self):

        console_log("event list:\n"+self.evtStr+"\nE for next, P for prev, S for summary, O for overview, N for none")
        reply = input("eid:").replace(" ", "")
        self.commandEid = reply

        eid = eType.NONE

        if reply.isdigit():
            eid = int(reply)
            if eid >= self.evtCnt:
                eid = self.evtCnt - 1
        elif reply in ("S","s"):
            eid = eType.SUMMARY
        elif reply in ("O","o"):
            eid = eType.OVERVIEW
        elif reply in ("E","e"):
            eid = eType.NEXT
        elif reply in ("P","p"):
            eid = eType.PREV
        
        return eid
    
    def discuss_progress(self):
        discussed = []
        todiscuss = []

        done_reply = ""
        todo_reply = ""
        next_todo = ""

        for i in range(self.evtCnt):
            desc = "场景{}:{},{}.".format(str(i+1), self.shorts[i], self.metas[i])
            if self.isEventTalked[i]:
                discussed.append(desc)
            else:
                todiscuss.append(desc)
        
        if len(discussed) == 0:
            done_reply = ""
        else:
            done_reply = "我们聊过了以下场景:"
            done_reply += ''.join(discussed)
        
        if len(todiscuss) == 0:
            todo_reply = "所有场景都简单聊过了。"
        else:
            next_todo = todiscuss[0]
            todo_reply = "还有以下场景没有聊过:"
            todo_reply += ''.join(todiscuss)
            todo_reply += "你想聊哪一个呢?"

        return done_reply, todo_reply, next_todo
    
    def state_controller(self):
        # determine the event
        eid = self.event_selector()

        for i in range(self.evtCnt):
            if self.isEventTalked[i]:
                self.forwardProgress = i
            else:
                break

        if eid == eType.NONE or eid == self.curEid:
            pass
        elif eid == eType.SUMMARY:
            self.summarizing = True
        elif eid == eType.OVERVIEW:
            self.wandering = True
            self.overviewing = True
        else:
            if self.wandering:
                if eid == eType.PREV or eid == self.forwardProgress:
                    self.wandering = False
                    self.curEid = self.forwardProgress
                elif eid == eType.NEXT or eid == self.forwardProgress + 1:
                    self.wandering = False
                    self.curEid = self.forwardProgress + 1
                else:
                    self.curEid = eid
            else:
                if (eid == eType.NEXT and self.curEid < self.evtCnt - 1) or eid == self.curEid + 1:
                    self.curEid += 1
                    self.forwardProgress = self.curEid
                elif (eid == eType.NEXT and self.curEid == self.evtCnt - 1):
                    self.summarizing = True
                elif eid == eType.PREV:
                    self.wandering = True
                    self.curEid -= 1
                else:
                    self.wandering = True
                    self.curEid = eid
            
    #
    #
    # ________________________ Response Functions ________________________
    def introduction(self):
        reply = self.superE + "我们从第一个场景聊起吧，第一个场景是{}。".format(self.shorts[self.curEid])
        self.chat_history.append({"role": "assistant", "content": reply})

        self.record_current_dialogue_turn(None, reply, None)

        return reply
    
    def generate_summary(self, user_input):
        content = []
        content.extend(self.chat_history)
        content.append({"role": "user", "content": user_input})

        task = "请根据上述对话历史，为用户生成一段回忆录。请忠于对话历史的表述，不要想象对话之外的内容。请将回复控制在200个字以内。:"
        content.append({"role": "user", "content": task})
        
        reply = "这组照片一共{}张，有{}个场景。我为您生成了以下回忆录:".format(str(self.photos[-1][-1]), str(self.evtCnt))
        reply += self.call_llm(content, max_tokens=800)

        return reply
    
    def overview(self):
        done, todo, next_todo = self.discuss_progress()

        progress = done + todo
            
        return progress

    def chat(self, user_input):
        self.commandEid = None
        # self.original_eid, self.corrected_eid = None, None

        self.state_controller()

        if self.summarizing:
            reply = self.generate_summary(user_input)
        elif self.overviewing:
            reply = self.overview()
        else:
            self.isEventTalked[self.curEid] = True
            reply = self.replier(user_input)
            console_log("Plain_Reply:"+reply)
            inspirations = self.inspirer()
            console_log("Inspiration:"+inspirations)
        
        corrected_reply = human_check_reply(reply) # None if original reply is accepted
        self.record_current_dialogue_turn(user_input, reply, corrected_reply)
        
        self.summarizing = False
        self.overviewing = False

        reply = corrected_reply if corrected_reply else reply 

        self.chat_history.append({"role": "user", "content": user_input})
        self.chat_history.append({"role": "assistant", "content": reply})

        return reply