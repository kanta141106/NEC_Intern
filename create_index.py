"""
Q&Aデータが記述されたCSVファイルを読み込み、
Elasticsearchにベクトル検索可能なインデックスとして登録する。
"""

import os
import sys
import pandas as pd
from elasticsearch import Elasticsearch
from transformers import AutoTokenizer, AutoModel
from sklearn.preprocessing import normalize
import urllib3
import warnings

# =========================================
# 警告を非表示にする設定
# =========================================
os.environ["TOKENIZERS_PARALLELISM"] = "false"
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore")

# =========================================
# ディレクトリパスの追加
# =========================================
sys.path.append('./RAG_program')
import utils
import synonym_dictionary

# =========================================
# エンベディングモデルの初期化
# =========================================
print("エンベディングモデルを読み込んでいます...")
tokenizer = AutoTokenizer.from_pretrained('./RAG_program/multilingual-e5-large')
model = AutoModel.from_pretrained('./RAG_program/multilingual-e5-large')
print("モデルの読み込みが完了しました。")

# =========================================
# 0. RAGのインデックス登録 関数
# =========================================
def rag_index_registration(csv_filepath):
    """
    CSVファイルからQ&Aデータを読み込み、Elasticsearchにベクトル検索可能なインデックスとして登録する関数
    """
    # Elasticsearchに接続
    es = Elasticsearch(
        utils.ElasticsearchInfo.URL.value, 
        basic_auth=(utils.ElasticsearchInfo.ID.value, utils.ElasticsearchInfo.PASS.value), 
        verify_certs=False
    )
    
    index_name = "rag_index"
    
    # 既存インデックスを削除して再作成
    if es.indices.exists(index=index_name):
        print(f"既存のインデックス '{index_name}' を削除します。")
        es.indices.delete(index=index_name)
    
    # インデックス設定
    index_config = {
        "settings": { "analysis": { "tokenizer": { "kuromoji_w_dic": {"type": "kuromoji_tokenizer"} }, "analyzer": { "jpn-search": { "type": "custom", "tokenizer": "kuromoji_w_dic", "filter": [ "kuromoji_baseform", "kuromoji_part_of_speech", "ja_stop", "kuromoji_number", "kuromoji_stemmer" ] } } } },
        "mappings": { "properties": { "uniqueID": {"type": "keyword"}, "body": {"type": "text", "analyzer": "jpn-search"}, "body_vector": {"type": "dense_vector", "dims": 1024}, "category": {"type": "keyword"}, "department_label": {"type": "keyword"}, "answer_content": {"type": "text", "analyzer": "jpn-search"} } }
    }
    
    print(f"新しいインデックス '{index_name}' を作成します。")
    es.indices.create(index=index_name, body=index_config)
    
    # CSVファイルを読み込み
    print(f"CSVファイル '{csv_filepath}' を読み込んでいます...")
    df = pd.read_csv(csv_filepath, encoding="utf-8-sig")
    print(f"{len(df.index)}件のデータを処理します。")
    
    # CSVの各行に対してループ処理
    for index, row in df.iterrows():
        body_text = synonym_dictionary.get_synonyms(str(row['本文']))
        
        batch_dict = tokenizer.encode_plus(
            body_text, add_special_tokens=True,
            padding='longest', truncation=True, return_tensors='pt'
        )
        outputs = model(**batch_dict)
        embeddings = outputs.last_hidden_state[:,0,:].detach().numpy()
        normalized_embeddings = normalize(embeddings)[0]
        
        doc = {
            'uniqueID': str(index).zfill(5),
            'body': body_text,
            'body_vector': normalized_embeddings.tolist(),
            'category': str(row['カテゴリ']),
            'department_label': str(row['担当課']),
            'answer_content': str(row['回答内容'])
        }
        
        es.index(index=index_name, id=doc['uniqueID'], document=doc)
        # 進捗がわかるように表示
        print(f"  - ID: {doc['uniqueID']} のデータを登録しました。")

    # 登録内容を即時検索可能にするためにインデックスをリフレッシュ
    es.indices.refresh(index=index_name)
    
    # 最終的に登録された件数をカウントして表示
    count_res = es.count(index=index_name)
    print('----------------------------------------')
    print('自動回答用インデックス登録件数: {}'.format(count_res["count"]))
    print('----------------------------------------')
    # Elasticsearchとの接続を閉じる
    es.close()

# =========================================
# 実行ブロック
# =========================================
if __name__ == "__main__":
    print("=== RAGデータ登録処理を開始します ===")
    # Q&Aデータが格納されているCSVファイルのパスを指定
    csv_file_path = "データ/rag_sample.csv"
    # データ登録関数を呼び出し
    rag_index_registration(csv_file_path)
    print("=== 全ての処理が完了しました ===")