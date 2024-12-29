# 老後資金シミュレーター

老後資金シミュレーターは、将来の生活費、貯金、年金収入をシミュレーションするアプリケーションです。このアプリケーションは、Google Cloud FunctionsとGoogle Cloud Storageを利用してホスティングされています。

## 概要
老後の資金計画を立てることを目的に、収入や生活費の推移をシミュレーションし、必要な老後資金を可視化します。計算結果はグラフとしてGoogle Cloud Storageに保存され、アプリ上で表示されます。

## デモURL
- 老後資金シミュレーター[https://storage.cloud.google.com/retirement-assets-simulator-frontend/index.html]

## 機能
- 年齢、生活費、貯金、年金開始年齢を入力し、老後に必要な資金の計算を実行します。
- 計算結果を可視化したグラフを表示します。

## 使い方
1. 上記のURLにアクセスします。
2. 各種入力フィールドに情報を入力し、「計算」をクリックします。
3. 結果ページで、老後資金の推移グラフと必要資金の詳細が表示されます。

## セットアップ手順

### 前提条件
- Python 3.9以降
- Google Cloudアカウントおよびプロジェクト

### インストールとローカル実行

1. リポジトリをクローンします。

    ```bash
    git clone https://github.com/kimura-sekishin/retirement_assets_simulator.git
    cd retirement-assets-simulator
    ```

2. 必要なパッケージをインストールします。

    ```bash
    pip install -r requirements.txt
    ```

3. `app/main.py`のローカルサーバーを起動してテストするには、Flaskを使用します。

    ```bash
    flask run
    ```

### GCPへのデプロイ

1. **Cloud Storage** バケットの作成  
   グラフ画像を保存するためのバケットを作成し、公開アクセスを有効にします。

2. **Cloud Functions** のデプロイ  
   アプリケーションのロジック（`main.py`）をCloud Functionsにデプロイします。

   ```bash
   gcloud functions deploy calculate \
       --runtime python39 \
       --trigger-http \
       --allow-unauthenticated \
       --region asia-northeast1
