"""
メール自動対応システム

システム概要:
顧客からの問い合わせメールを1件ずつリアルタイムに受け取り、
「自動回答生成」または「担当部署の割り当て」を判断し、結果を出力する。
"""

import os
import sys
from openai import OpenAI
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
current_dir = os.path.dirname(os.path.abspath(__file__))
rag_program_path = os.path.join(current_dir, '..', 'RAG_program')
if rag_program_path not in sys.path:
    sys.path.append(rag_program_path)
import utils
import synonym_dictionary

# =========================================
# OpenAI APIクライアントの初期化
# =========================================
client = OpenAI(
    api_key=os.getenv("COTOMIAPI_API_KEY"),
    base_url=os.getenv("COTOMIAPI_OAI_ENDPOINT")
)

# =========================================
# エンベディングモデルの初期化
# =========================================
model_path = os.path.join(current_dir, '..', 'RAG_program', 'multilingual-e5-large')

tokenizer = AutoTokenizer.from_pretrained(model_path)
model = AutoModel.from_pretrained(model_path)

# =========================================
# プロンプト読み込みユーティリティ
# =========================================
def load_prompt(filename):
    """
    プロンプト/ フォルダから指定ファイルを読み込む
    """
    prompt_path = os.path.join(os.path.dirname(__file__), "プロンプト", filename)
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()

# =========================================
# 1. メイン処理 関数
# =========================================
def main_process(category, body_text):
    can_answer, search_chunks = similar_qa_search(category, body_text)
    
    if can_answer:
        result = auto_reply_generation(body_text, search_chunks)
        print("自動回答を生成しました。")
    else:
        result = department_assignment(body_text, search_chunks)
        print("担当部署を割り当てました: {}".format(result))
    
    return result

# =========================================
# 2. 類似QA検索 関数
# =========================================
def similar_qa_search(category, body_text):
    es = Elasticsearch(
        utils.ElasticsearchInfo.URL.value, 
        basic_auth=(utils.ElasticsearchInfo.ID.value, utils.ElasticsearchInfo.PASS.value), 
        verify_certs=False
    )
    
    index_name = "rag_index"
    processed_text = synonym_dictionary.get_synonyms(body_text)
    
    batch_dict = tokenizer.encode_plus(
        processed_text, add_special_tokens=True,
        padding='longest', truncation=True, return_tensors='pt'
    )
    outputs = model(**batch_dict)
    embeddings = outputs.last_hidden_state[:,0,:].detach().numpy()
    normalized_embeddings = normalize(embeddings)[0]
    
    script_query = {
        "script_score": {
            "query": { "bool": { "must": [ {"match_all": {}}, {"term": {"category": category}} ] } },
            "script": { "source": "cosineSimilarity(params.query_vector, 'body_vector') + 1.0", "params": {"query_vector": normalized_embeddings.tolist()} }
        }
    }
    
    vector_res = es.search(
        index=index_name,
        body={ "query": script_query, "size": 5, "sort": [{"_score": {"order": "desc"}}], "_source": ["body", "answer_content", "category", "department_label"] }
    )
    es.close()
    
    search_chunks = []
    for hit in vector_res['hits']['hits']:
        search_chunks.append({
            'body': hit['_source']['body'], 'answer': hit['_source']['answer_content'],
            'similarity': hit['_score'], 'category': hit['_source']['category'],
            'department': hit['_source']['department_label']
        })
    
    if not search_chunks:
        return False, []
    
    qa_prompt_template = load_prompt("回答可能性判断プロンプト.md")
    chunks_text = ""
    for i, chunk in enumerate(search_chunks, 1):
        chunks_text += f"\n--- 候補{i} (類似度: {chunk['similarity']:.3f}) ---\n担当部署: {chunk['department']}\n質問: {chunk['body']}\n回答: {chunk['answer']}\n"
    
    qa_prompt = qa_prompt_template.format(body_text=body_text, search_chunks=chunks_text)
    
    response = client.chat.completions.create(
        model="cotomi-fast-v2.0",
        messages=[{"role": "system", "content": qa_prompt}],
    )
    judgment = response.choices[0].message.content
    can_answer = "不可能" not in judgment
    return can_answer, search_chunks

# =========================================
# 3. 自動返信生成 関数
# =========================================
def auto_reply_generation(body_text, search_chunks):
    reply_prompt_template = load_prompt("回答作成プロンプト.md")
    
    chunks_text = ""
    for i, chunk in enumerate(search_chunks, 1):
        chunks_text += f"\n--- 参考情報{i} ---\n関連質問: {chunk['body']}\n回答内容: {chunk['answer']}\n"
    
    reply_prompt = reply_prompt_template.format(body_text=body_text, search_chunks=chunks_text)
    
    response = client.chat.completions.create(
        model="cotomi-fast-v2.0",
        messages=[{"role": "system", "content": reply_prompt}],
    )
    return response.choices[0].message.content

# =========================================
# 4. 担当部署割り振り関数
# =========================================
def department_assignment(body_text, search_chunks):
    assign_prompt_template = load_prompt("担当部署振分プロンプト.md")
    assign_prompt = assign_prompt_template.format(body_text=body_text, search_chunks=search_chunks)
    
    response = client.chat.completions.create(
        model="cotomi-fast-v2.0",
        messages=[{"role": "system", "content": assign_prompt}],
    )
    return response.choices[0].message.content.strip()

# =========================================
# 実行例
# =========================================
if __name__ == "__main__":
    # -------------------------------
    # メール自動対応処理のテスト
    # -------------------------------
    test_category = "店舗情報"
    test_body = "〇〇店の営業時間を教えてください"
    
    print("=== メール自動対応システム テスト ===")
    print("カテゴリ:", test_category)
    print("問い合わせ内容:", test_body)
    print()
    
    result = main_process(test_category, test_body)
    
    print("=== 処理結果 ===")
    print(result)