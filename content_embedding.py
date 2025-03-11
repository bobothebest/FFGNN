# -*- coding: utf-8 -*-
"""content embedding.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1peBZe1xZxncYpPZuKOnzKR0JAXPCi4IV
"""

import pandas as pd
from google.colab import drive

# 挂载 Google Drive
drive.mount('/mnt/drive')

"""# DBLP添加了用户信息和文章信息embedding的训练

## 修改数据处理部分来包含摘要信息
"""

# 定义观察时间窗口
T_0 = 2010  # 设置观察截止年份

class DBLPProcessor:
    def __init__(self, model_name='allenai/scibert_scivocab_uncased', device='cuda'):
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModel.from_pretrained(model_name)
        self.device = device
        self.model.to(device)
        self.model.eval()

    def parse_dblp_with_text(self, file_path, T_0):
        """解析DBLP文件，包含标题和摘要信息"""
        graph = defaultdict(list)
        timestamps = {}
        paper_texts = {}  # 存储论文的标题和摘要

        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
            papers = content.strip().split("\n\n")

            for paper in papers:
                index_match = re.search(r"#index(\d+)", paper)
                year_match = re.search(r"#t(\d+)", paper)
                title_match = re.search(r"#\*(.*)", paper)
                abstract_match = re.search(r"#!(.*)", paper)
                references = re.findall(r"#%(\d+)", paper)

                if index_match and year_match:
                    paper_index = int(index_match.group(1))
                    year = int(year_match.group(1))

                    if year <= T_0:
                        timestamps[paper_index] = year

                        # 组合标题和摘要
                        text_parts = []
                        if title_match:
                            text_parts.append(title_match.group(1).strip())
                        if abstract_match:
                            text_parts.append(abstract_match.group(1).strip())

                        # 如果有任何文本，则保存
                        if text_parts:
                            paper_texts[paper_index] = " ".join(text_parts)

                        for ref in references:
                            ref_index = int(ref)
                            graph[paper_index].append(ref_index)

        return graph, timestamps, paper_texts

    @torch.no_grad()
    def get_text_embedding(self, text):
        """使用SciBERT生成文本的嵌入向量"""
        try:
            inputs = self.tokenizer(text,
                                  return_tensors="pt",
                                  truncation=True,
                                  max_length=512,
                                  padding=True)

            # 将输入移到正确的设备上
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            outputs = self.model(**inputs)
            # 使用[CLS]令牌的最后隐藏状态作为文本的表示
            embedding = outputs.last_hidden_state[:, 0, :].cpu().numpy()
            return embedding.flatten()
        except Exception as e:
            print(f"Error processing text: {e}")
            return np.zeros(768)  # 返回零向量作为默认嵌入

    def process_paper_texts_batch(self, paper_texts, batch_size=32):
        """批量处理论文文本，生成嵌入"""
        paper_features = {}
        paper_ids = list(paper_texts.keys())

        for i in range(0, len(paper_ids), batch_size):
            batch_ids = paper_ids[i:i + batch_size]
            batch_texts = [paper_texts.get(pid, "") for pid in batch_ids]

            # 处理这个批次
            for pid, text in zip(batch_ids, batch_texts):
                if text.strip():  # 只处理非空文本
                    embedding = self.get_text_embedding(text)
                    paper_features[pid] = embedding

            if (i + batch_size) % 1000 == 0:
                print(f"Processed {i + batch_size} papers")

        return paper_features

    def build_and_save_cascades_with_features(self, graph, timestamps, paper_texts,
                                            output_path, feature_path):
        """构建级联并保存，包括文本特征"""
        # 首先生成所有文本的嵌入特征
        print("Generating paper embeddings...")
        paper_features = self.process_paper_texts_batch(paper_texts)

        # 保存特征
        print(f"Saving features to {feature_path}")
        np.save(feature_path, paper_features)

        # 保存级联信息
        print(f"Saving cascade information to {output_path}")
        cascade_id = 0
        row_id = 0

        with open(output_path, "w", newline="", encoding="utf-8") as file:
            writer = csv.DictWriter(file, fieldnames=["Unnamed: 0", "cas", "src",
                                                    "target", "ts", "label", "e_idx"])
            writer.writeheader()

            for src, targets in graph.items():
                if len(targets) == 0:
                    continue

                e_idx = 1
                label = len(targets)

                for target in targets:
                    writer.writerow({
                        "Unnamed: 0": row_id,
                        "cas": cascade_id,
                        "src": src,
                        "target": target,
                        "ts": timestamps.get(target, -1),
                        "label": label,
                        "e_idx": e_idx
                    })
                    row_id += 1
                    e_idx += 1
                cascade_id += 1

        return paper_features

# 定义输出路径
output_path = '/mnt/drive/MyDrive/social_network/codes/HierCas-master/processed/DBLP_process.csv'
feature_path = '/mnt/drive/MyDrive/social_network/codes/HierCas-master/processed/paper_features.npy'
dblp_with_cite_path = '/mnt/drive/MyDrive/social_network/data/DBLP_withcite.txt'

# 1. 处理数据
print(f"Processing DBLP data with observation window until year {T_0}")
processor = DBLPProcessor(device='cuda')  # 或 'cpu'
graph, timestamps, paper_texts = processor.parse_dblp_with_text(dblp_with_cite_path, T_0)

print(f"Found {len(paper_texts)} papers with text content")
print(f"Found {len(graph)} papers with citations")

# 2. 生成级联数据和特征
paper_features = processor.build_and_save_cascades_with_features(
    graph,
    timestamps,
    paper_texts,
    output_path,
    feature_path
)

dblp_process_path = '/mnt/drive/MyDrive/social_network/codes/HierCas-master/processed/DBLP_process.csv'
dblp_process = pd.read_csv(dblp_process_path)

dblp_process

"""## 训练模型"""

# Commented out IPython magic to ensure Python compatibility.
# 前97条
# %cd /mnt/drive/MyDrive/social_network/codes/FFGNN
!python train.py --data DBLP_20_sample --gpu 0

# 文件路径
DBLP_process_20_path = '/mnt/drive/MyDrive/social_network/codes/FFGNN/processed/ml_DBLP_process_20.csv'

# 加载原始数据
try:
    DBLP_20_data = pd.read_csv(DBLP_process_20_path)
    print(f"Loaded {len(DBLP_20_data)} rows from {DBLP_process_20_path}.")
except FileNotFoundError:
    print(f"File not found at {DBLP_process_20_path}. Please check the path.")
    raise

# 提取前 100 条数据
DBLP_20_sample = DBLP_20_data.head(999)

# 保存提取的数据到原地址
DBLP_20_sample_path = '/mnt/drive/MyDrive/social_network/codes/FFGNN/processed/ml_DBLP_20_sample.csv'
DBLP_20_sample.to_csv(DBLP_20_sample_path, index=False)
print(f"Saved first 100 rows to {DBLP_20_sample_path}.")

DBLP_20_sample

# Commented out IPython magic to ensure Python compatibility.

# %cd /mnt/drive/MyDrive/social_network/codes/FFGNN
!python train.py --data DBLP_20_sample --gpu 0

!python train.py --data DBLP_process_20 --gpu 0

!python train.py --data DBLP_process_10 --gpu 0 --n_epoch 20

!python train.py --data DBLP_process_20 --gpu 0 --n_epoch 20

