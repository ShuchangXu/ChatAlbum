import os
import threading
from openai import OpenAI
from datetime import datetime

TIME_OUT = 30

class Reviver:
    def __init__(self, api_key):
        # ________ This is the Memory Tree ________
        # Photo Information
        self.superE = None #"18年秋天，在青岛拍摄，一共有25张照片。其中有XXX，XXX等场景。"
        self.evtCnt = 0 # number of events
        self.events = None
        # self.photos = None
        self.talked = None

        # User Narrations
        self.super_narrations = None
        self.event_narrations = None

        # ________ This is the info passed into LLM ________
        # Photo Info
        self.events_string = None
        self.photos_string = None

        # Chat History
        self.chat_history = []
        
        # System Guide
        self.event_selector = open("./Reviver/prompts/event_selector", 'r', encoding='utf-8').read()
        self.inspirer = open("./Reviver/prompts/inspirer", 'r', encoding='utf-8').read()

        # ________ OpenAI client ________
        self.client = OpenAI(api_key=api_key, timeout=TIME_OUT)
        self.lock = threading.Lock()
    
    def init_mtree(self):
        self.superE = "18年10月份在北京拍摄的照片，一共有29张。照片里有你和几位成年人，去了天安门、故宫、动物园、鸟巢等地方。天气晴朗。"
        self.events = ["晴朗天气下，参观天安门广场的照片,拍摄了3张合影。和您一起合影的人，有一位中年男子，一位中年女子，以及一位青年男子。",
                       "晴朗天气下，参观故宫博物院的照片,拍摄了8张合影。",
                       "在动物园参观老虎和白狮,拍摄了10张动物照片。",
                       "在动物园参观刺猬,拍摄了3张照片。",
                       "傍晚，参观颐和园和鸟巢,拍摄了5张照片。"
                       ]
        self.evtCnt = len(self.events)
        self.talked = [0] * self.evtCnt
        self.events_string = """0 参观天安门广场\n
                                1 参观故宫博物院\n
                                2 在动物园参观老虎和白狮\n
                                3 在动物园参观刺猬\n
                                4 参观颐和园和鸟巢\n
                             """
        self.photos_string = [
            """
                1  您站在天安门前，身边是一位女士和一位男士，背景是蓝天和人群。
                2  您与三位家人站在天安门前，蓝天下的午后，人群熙熙攘攘。
                3  您与三人站在天安门前，天气晴朗，背后是人群和蓝天。
            """,
            """
                4  三人站在故宫门前，男子中间，天气晴朗。
                5  您正站在三人中间，背后书有“中华门”字样的朱红城门。
                6  用户位于照片中间，身穿白衬衫和背带裤，天安门前合影，晴天。
                7  故宫广场上，两人站立，游客穿梭，天气晴朗。
                8  您与另一位男士站在故宫博物院的广场上，背景是宏伟的红墙和琉璃瓦房顶。周围是游客和蓝天。
                9  您和另一位男士站在故宫广场上，背景是古建筑，天空晴朗。
                10 您在故宫太和殿前，天气晴朗，与一位朋友并肩站立，游客众多。
                11 您在紫禁城的广场上，与两位亲人站立，背后是午门。阳光明媚，人群熙熙攘攘。
            """,
            """
                12 一只虎正走动，前方有禁止敲击、喂食和使用闪光的提示牌。
                13 一只雄壮的白狮侧身站立，显得威严而从容。
                14 这是一只雄赳的白狮，站立着侧面望向远处。
                15 一只棕白相间的雄狮正站立，环顾四周，背景是土地和少许绿植。
                16 一只白狮站在树荫地，看起来很壮观。
                17 一只坐着的白狮，显得很沉思。
                18 一只站立和一只躺着的白狮，阳光下，有树木和遮阳棚。
                19 两只白狮在树荫下休息，一只躺着，一只站着。
                20 两只狮子，一只金色雄狮在走动，一只白色雌狮在休息。
                21 一只白狮伸展身体，坐在阳光下的地面上。
            """,
            """
                22 照片有点模糊，像是一只动物在吃东西，具体不清晰。
                23 这是一张刺猬的特写照片，其正在地面上，有明显的白色刺。
                24 这是一张拍摄质量较低的照片，显示了一只模糊的豪猪侧面图像。
            """,
            """
                25 男子站在古建筑前，穿黑色运动装，背后蓝天晴朗。
                26 男子站在宽敞的石地上，背后是古典中国式建筑群，天空晴朗。
                27 两位男士站在古建筑前，天气晴朗，周围有游客。
                28 这位女士站在有钢结构的建筑前，阳光下，背影有人经过。
                29 您站在一个宽阔的广场上，背后是结构复杂的鸟巢体育场。天色渐暗，人们散步。
            """
        ]
        
        
    def call_llm(self, content, max_tokens = 200, model="gpt-4-vision-preview"):
        response = self.client.chat.completions.create(
            messages = content,
            model = model,
            max_tokens = max_tokens
        )

        reply = response.choices[0].message.content
        return reply
        

    def select_event(self, user_input):
        content = []
        content.append({"role": "system", "content": self.event_selector})
        content.extend(self.chat_history)

        task = "以上是对话历史。你的任务是，根据对话历史，根据以下用户输入判断，用户想了解的是哪一个事件。请直接回复事件编号。"
        task += "用户输入是:" + user_input + "\n"
        task += "请在以下事件中选择一个:" + self.events_string + "\n"
        content.append({"role": "user", "content": task})
        
        reply = self.call_llm(content)

        return reply

    
    def inspire(self, user_input, eid):
        content = []
        content.append({"role": "system", "content": self.inspirer})
        content.extend(self.chat_history)

        # ________ Answer Strategy ________
        task = "以上是对话历史。你的任务是:根据对话历史和照片信息，回复用户的输入。\
                请切记: \
                (1) 你的回答必须基于照片信息，不要想象和发挥。\
                (2) 在你的回答中，简单呼应用户后(比如:'你说得对','确实如此','照片里没有看到你说的内容')，不要再重复对话历史中讨论过的信息。请提供新信息。\
                (3) 请直接提供回复。你的回答要尽可能简短。\n"
        task += "你需要回答的用户输入是:"+user_input+"\n"
        task += "你必须基于以下照片信息提供回复:"+self.photos_string[eid] + "\n"

        # ________ Inspire Strategy ________
        print("LOG:事件"+str(eid)+",讨论次数:"+str(self.talked[eid]))
        if self.talked[eid] == 0:
            task += "请在你的回答中，包含如下概述:" + self.events[eid] + "\n"
            task += "并在最后询问: 你还记得当时的情景吗?"
        
        elif self.talked[eid] < 3:
            task += "除了回答用户问题，请你提供照片内未讨论的新信息(比如新的主体、新的活动)。请确保你的回答简短，且有组织性。"
            task += "请你最后挑一个问题询问用户:(1)你的心情如何?(2)你还有印象吗?(3)什么令你印象深刻?"

        else:
            next_eid = - 1
            for i in range(1, self.evtCnt):
                id = (eid+i) % self.evtCnt
                # print("LOG:遍历事件"+str(id)+",讨论次数:"+str(self.talked[id]))
                if self.talked[id] == 0:
                    next_eid = id
                    break
            if next_eid == -1:
                task += "请在回复最后，告诉用户: 所有场景都简单聊过了。然后简单概括下对话历史中讨论过的场景，最后询问用户:你还想聊哪个场景?还是为您生成一段回忆录呢?"
            else:
                task += "请在回复最后,简短询问用户，要不要聊其他场景。你要建议的场景是:" + self.events[next_eid]

        content.append({"role": "user", "content": task})

        # ________ Get Reply ________
        reply = self.call_llm(content)

        self.talked[eid] = self.talked[eid] + 1

        return reply

    def onboarding(self):
        reply = "这是" + self.superE + "对这段经历，你的印象如何?"
        self.chat_history.append({"role": "assistant", "content": reply})

        return reply
    
    def chat(self, user_input):
        # TODO:: save_narration()

        # TODO:: terminator first (do users hope to terminate the discussion?)

        # retrieve a relevant event
        # TODO:: exception handler
        eid_string = self.select_event(user_input)
        eid = int(eid_string)

        # get a reply
        reply = self.inspire(user_input, eid)

        self.chat_history.append({"role": "user", "content": user_input})
        self.chat_history.append({"role": "assistant", "content": reply})

        return reply
    
    def save_chat_history(self, prefix):
        log_prefix = prefix + '_' + datetime.now().strftime("%Y%m%d")
        log_postfix = 0        
        with self.lock:
            for filename in os.listdir("./Reviver/logs"):
                if filename.startswith(log_prefix):
                    log_postfix += 1
        log_path = "./logs/{}_{}.log".format(log_prefix, log_postfix)

        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(self.chat_history)
        print("本次聊天记录已保存至", log_path)