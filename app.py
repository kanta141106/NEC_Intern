import streamlit as st
import sys
import os

# =========================================
# 外部モジュールのインポート設定
# =========================================
# --- 問い合わせ対応システムのインポート ---
from 問い合わせ対応.main import main_process as response_process
RESPONSE_SYSTEM_AVAILABLE = True

# --- 問い合わせ分析システムのインポート ---
from 問い合わせ分析.main import main_process as analysis_process
ANALYSIS_SYSTEM_AVAILABLE = True

# =========================================
# 問い合わせ対応ページの描画関数
# =========================================
def page_inquiry_response():
    st.title("問い合わせ自動対応システム")

    # --- ユーザー入力 ---
    st.subheader("問い合わせ内容の入力")

    category_options = ["店舗情報", "選択肢2", "選択肢3"]
    category = st.selectbox(
        "カテゴリ",
        options=category_options,
        help="問い合わせのカテゴリを選択してください。"
    )

    body_text = st.text_area(
        "本文",
        "", 
        height=200,
        help="問い合わせの具体的な内容を入力してください。"
    )

    # --- 実行ボタン ---
    if st.button("処理を実行する", type="primary"):
        if not category or not body_text.strip(): 
            st.warning("カテゴリを選択し、本文を入力してください。")
        else:
            with st.spinner("処理を実行中... (Elasticsearch検索とLLM応答には時間がかかることがあります)"):
                try:
                    # 問い合わせ対応のメイン処理を呼び出す
                    result = response_process(category, body_text)
                    st.subheader("処理結果")
                    st.success("処理が正常に完了しました。")
                    # 結果を整形して表示
                    st.markdown(f"```text\n{result}\n```")
                except Exception as e:
                    st.error(f"処理中にエラーが発生しました: {e}")

# =========================================
# 問い合わせ分析ページの描画関数
# =========================================
def page_inquiry_analysis():
    st.title("問い合わせ自動分析システム")

    # --- ユーザー入力 ---
    st.subheader("分析条件の入力")
    analysis_count = st.number_input(
        "分析対象とする最新メールの件数",
        min_value=1,
        max_value=1000,
        value=50,
        step=10,
        help="Elasticsearchから取得する最新のメール件数を指定します。"
    )

    # --- 実行ボタン ---
    if st.button("分析レポートを生成する", type="primary"):
        with st.spinner(f"最新{analysis_count}件のメールを分析中... (LLMによる分析には時間がかかります)"):
            try:
                # 問い合わせ分析のメイン処理を呼び出す
                report = analysis_process(analysis_count=analysis_count)
                st.session_state['report'] = report 
                st.success("レポート生成が完了しました。")
            except Exception as e:
                st.error(f"分析中にエラーが発生しました: {e}")
                st.session_state.pop('report', None) # エラー時にレポートをクリア

    # --- 結果表示 ---
    if 'report' in st.session_state and st.session_state['report']:
        st.subheader("分析レポート")
        
        report_dict = st.session_state['report']
        
        # ダウンロード用に全レポートを結合したテキストを作成
        full_report_text = ""
        for category, report_content in report_dict.items():
            full_report_text += f"========== カテゴリ: {category} ==========\n\n{report_content}\n\n\n"

        # カテゴリごとにエキスパンダー（折りたたみUI）で表示
        for category, report_content in report_dict.items():
            with st.expander(f"カテゴリ: {category} のレポート"):
                st.markdown(report_content.replace("\n", "  \n"))

# =========================================
# Streamlit アプリケーション本体
# =========================================
def main():
    st.sidebar.title("システム選択")
    # サイドバーで表示するページを選択
    page = st.sidebar.radio(
        "どちらのシステムを利用しますか？",
        ("問い合わせ自動対応システム", "問い合わせ自動分析システム")
    )

    # 選択されたページに応じて対応する関数を呼び出す
    if page == "問い合わせ自動対応システム":
        if RESPONSE_SYSTEM_AVAILABLE:
            page_inquiry_response()
        else:
            st.error("'問い合わせ対応'システムの読み込みに失敗したため、この機能は利用できません。")

    elif page == "問い合わせ自動分析システム":
        if ANALYSIS_SYSTEM_AVAILABLE:
            page_inquiry_analysis()
        else:
            st.error("'問い合わせ分析'システムの読み込みに失敗したため、この機能は利用できません。")

# --- アプリケーションの実行 ---
if __name__ == "__main__":
    main()