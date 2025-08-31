# セットアップ手順 (Windows向け)

このドキュメントは、`NEC_Intern` プロジェクトをWindows環境でセットアップし、実行するための詳細な手順を説明します。

---

### ステップ1: プロジェクトの準備

#### 1-1. Gitリポジトリのクローン

まず、このプロジェクト（`NEC_Intern`）を任意の作業フォルダにクローンします。

```bash
git clone https://github.com/kanta141106/NEC_Intern
```

#### 1-2. `RAG_program` フォルダの配置

次に、事前にNECから配布されている `RAG_program` フォルダを、クローンした `NEC_Intern` フォルダの直下に配置します。

**最終的なフォルダ構成:**
```
作業フォルダ/
└── NEC_Intern/
    ├── RAG_program/  <-- このフォルダをここに配置
    ├── 問い合わせ対応/
    ├── 問い合わせ分析/
    ├── app.py
    └── ... (その他のファイル)
```

---

### ステップ2: Python環境の構築

コマンドプロンプトまたはPowerShellを開き、`NEC_Intern` フォルダに移動してから、以下のコマンドを順に実行します。

```bash
# 1. NEC_Intern フォルダに移動
cd path\to\NEC_Intern

# 2. Python仮想環境を作成 (フォルダ内に myenv が作成されます)
python -m venv myenv

# 3. 仮想環境を有効化
.\myenv\Scripts\activate
```
コマンドプロンプトの行頭に `(myenv)` と表示されれば、仮想環境が正常に有効化されています。

```bash
# 4. 必要なライブラリをインストール
pip install -r requirements.txt
```

---

### ステップ3: Elasticsearchの起動

Elasticsearchサーバーを起動します。このサーバーはアプリケーションが動作している間、常に起動している必要があります。

1.  **新しいコマンドプロンプト**をもう一つ開きます。（これまでのターミナルはそのままにしておきます）

2.  新しいコマンドプロンプトで、`RAG_program` 内のElasticsearchが格納されているフォルダに移動します。
    ```bash
    cd path\to\NEC_Intern\RAG_program\install\elasticsearch-8.14.0
    ```

3.  以下のコマンドでElasticsearchを起動します。
    ```bash
    .\bin\elasticsearch.bat
    ```

実行後、このコマンドプロンプトには大量のログが表示され始めます。**このウィンドウはアプリケーションを使用中、ずっと開いたままにしておいてください。**

---

### ステップ4: Elasticsearchへのデータ登録 (初回のみ)

Elasticsearchサーバーが起動したら、次にRAGデータを登録します。

1.  **ステップ2で使っていた元のコマンドプロンプト**（`(myenv)` が表示されている方）に戻ります。

2.  `NEC_Intern` のルートディレクトリにいることを確認し、以下のコマンドを実行します。
    ```bash
    python create_index.py
    ```
この処理は、`データ/rag_sample.csv` を読み込み、ベクトルデータを計算してElasticsearchに登録します。処理が完了するまで数分待ちます。

---

### ステップ6: アプリケーションの実行

全ての準備が整いました。以下のコマンドでStreamlitアプリケーションを起動します。

1.  **ステップ5と同じコマンドプロンプト**（`(myenv)` が表示されている方）で、以下のコマンドを実行します。
    ```bash
    streamlit run app.py
    ```
2.  ターミナルに表示されたURL（通常は `http://localhost:8501`）をWebブラウザで開きます。

以上でアプリケーションの画面が表示されます。