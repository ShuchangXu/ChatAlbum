import sys
import json
import torch
import torch.nn.functional as F
# from text2vec import SentenceModel
# from text2vec import Word2Vec
from sentence_transformers import SentenceTransformer# Load model directly
from transformers import AutoTokenizer, AutoModelForMaskedLM



sys.path.append('..')



class SimilarityCalculator:
    def __init__(self, json_path="./photos/text_des_P7.json", model="shibing624/text2vec-base-chinese") -> None:
        # self.model = SentenceModel("shibing624/text2vec-base-chinese")
        # self.model = Word2Vec("w2v-light-tencent-chinese")
        # tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
        # model = AutoModelForMaskedLM.from_pretrained("bert-base-uncased")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.sentences = []
        self.embeddings = self.get_embedding_vectors(json_path)
        
        
    def get_embedding_vectors(self, path):
        json_file = open(path, 'r', encoding='utf-8').read()
        json_data = json.loads(json_file)
        
        embeddings = []
        for _, value in json_data.items():
            sentence = value["base"]["tit"]
            self.sentences.append(sentence)
            embedding = torch.tensor(self.model.encode(sentence))            
            embeddings.append(embedding.unsqueeze(0))
                       
        return torch.cat(embeddings, dim=0)
            
        
    def get_most_similar(self, query):
        print("\nQuery:", query)
        embedding = torch.tensor(self.model.encode(query))
        results = F.cosine_similarity(embedding, self.embeddings)
        # print(results)
        
        max_value = torch.max(results)
        cur_max = max_value
        count = 0
        while cur_max > 0.9 * max_value or count < 3:
            id = torch.argmax(results)
            print(int(id+1), self.sentences[id])
            results[id] = 0
            cur_max = torch.max(results)
            count += 1


if __name__ == "__main__":
    mCal = SimilarityCalculator()
    mCal.get_most_similar("我和男性友人的合影")
    mCal.get_most_similar("狮子在休息")
    # mCal.get_most_similar("狮子在休息吗？")
    # mCal.get_most_similar("我去了故宫的哪些地方")
    # mCal.get_most_similar("午门长什么样的")
    
    # 中文句向量模型(CoSENT)，中文语义匹配任务推荐，支持fine-tune继续训练
    # t2v_model = SentenceModel("shibing624/text2vec-base-chinese")
    # compute_emb(t2v_model)

    # # 支持多语言的句向量模型（CoSENT），多语言（包括中英文）语义匹配任务推荐，支持fine-tune继续训练
    # sbert_model = SentenceModel("shibing624/text2vec-base-multilingual")
    # compute_emb(sbert_model)

    # # 中文词向量模型(word2vec)，中文字面匹配任务和冷启动适用
    # w2v_model = Word2Vec("w2v-light-tencent-chinese")
    # compute_emb(w2v_model)