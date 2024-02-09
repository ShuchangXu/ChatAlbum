

class Photo:
    def __init(self, pid, desc):
        self.id = pid
        self.desc = desc

class Event:
    def __init__(self, eid, desc, pids):
        self.id = eid
        self.desc = desc
        self.pids = pids # id to Photos
        self.narration = []
        

class MemoryTree:
    def __init__(self):
        self.o = None # overview event
        self.e_list = [] # event list
        self.p_list = [] # photo list
    
    def init_photos(self, p_descs):
        for pid in range(len(p_descs)):
            self.p_list.append(Photo(pid, p_descs[pid]))
    
    def init_events(self, e_descs, e_pids):
        for
        


if __name__ == "__main__":
    p_descs = [
        "照片1描述",
        "照片2描述"
    ],
    
    = {}