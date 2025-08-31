"""
メール分析システム

システム概要:
データベース(Elasticsearch)に蓄積されたメールデータを参照し、
カテゴリごとに要約・分析したレポートを生成する。
"""

import os
import sys
from openai import OpenAI
from elasticsearch import Elasticsearch
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

# =========================================
# OpenAI APIクライアントの初期化
# =========================================
client = OpenAI(
    api_key=os.getenv("COTOMIAPI_API_KEY"),
    base_url=os.getenv("COTOMIAPI_OAI_ENDPOINT")
)

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
def main_process(analysis_count):
    """
    Elasticsearchから最新のメールデータを指定件数取得し、
    カテゴリごとに要約したレポートを生成する。
    
    引数:
        analysis_count (int): 分析対象とするメールの総数
    """
    # 1. Elasticsearchから分析対象のメールデータを取得
    print(f"Elasticsearchから最新のメールを{analysis_count}件取得しています...")
    es = Elasticsearch(
        utils.ElasticsearchInfo.URL.value, 
        basic_auth=(utils.ElasticsearchInfo.ID.value, utils.ElasticsearchInfo.PASS.value), 
        verify_certs=False
    )
    
    index_name = "rag_index"
    
    # uniqueIDの降順でソートすることで、最新のデータから取得する
    response = es.search(
        index=index_name,
        size=analysis_count,
        sort=[{"uniqueID": {"order": "desc"}}],
        _source=["category", "body"] 
    )
    hits = response['hits']['hits']
    
    es.close()
        
    # 2. 各カテゴリごとに本文リストを作成
    category_emails = {}
    for hit in hits:
        source = hit['_source']
        category = source.get('category', '未分類').strip()
        body = source.get('body', '').strip()
        
        if category and body:
            if category not in category_emails:
                category_emails[category] = []
            category_emails[category].append(body)
    
    print(f"\n分析開始: {len(category_emails)}カテゴリを処理します")
    
    category_reports = {}
    
    # 3. ループ処理で「カテゴリごとレポート作成 関数」を実行
    for category, email_list in category_emails.items():
        print(f"カテゴリ '{category}' の分析中... (件数: {len(email_list)})")
        report = create_category_report(category, email_list)
        
        category_reports[category] = report
    
    return category_reports

# =========================================
# 2. カテゴリごとレポート作成 関数
# =========================================
def create_category_report(category, email_body_list):
    """
    特定カテゴリのメール本文リストを要約・分析し、レポートを生成する。
    """
    # プロンプトテンプレートを読み込み
    report_prompt_template = load_prompt("レポート作成プロンプト.md")
    
    # メール本文をテキスト化
    email_samples_text = ""
    for i, email_body in enumerate(email_body_list, 1):
        email_samples_text += f"\n--- メール{i} ---\n{email_body}\n"
    
    # プロンプトを構築
    report_prompt = report_prompt_template.format(
        category=category,
        email_samples=email_samples_text,
        email_count=len(email_body_list)
    )
    
    # LLMを使用してレポート生成
    response = client.chat.completions.create(
        model="cotomi-fast-v2.0",
        messages=[{"role": "system", "content": report_prompt}],
    )
    report = response.choices[0].message.content

    return report

# =========================================
# 実行例
# =========================================
if __name__ == "__main__":
    # 分析対象とするメールの総数を設定
    ANALYSIS_TARGET_COUNT = 50 
    
    print("=== メール分析システム ===")
    print(f"分析対象: 最新 {ANALYSIS_TARGET_COUNT} 件のメール")
    print()
    
    # メイン処理実行
    result = main_process(analysis_count=ANALYSIS_TARGET_COUNT)
    
    print("\n=== 分析結果 ===")
    print(result)