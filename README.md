# お土産レコメンドアプリ on AWS Bedrock

## プロジェクト概要

このプロジェクトは、AWS Bedrock の生成AI能力を活用して、日本の各都道府県の代表的なお土産候補と、お土産を選ぶ際のポイントを推薦するシンプルなウェブアプリケーションです。サーバーレスアーキテクチャを採用しており、インフラ管理の負担を最小限に抑えつつ、スケーラブルなバックエンドシステムを実現しています。

開発者は、フロントエンド（HTML, CSS, JavaScript）と、API Gateway、Lambda、Bedrock を組み合わせたバックエンドを構築し、両者を連携させます。

## 機能

- ユーザーはウェブページ上の入力フォームに都道府県名を入力し、送信ボタンをクリックします。
- 入力された都道府県名は API Gateway を経由して AWS Lambda 関数に渡されます。
- Lambda 関数は受け取った都道府県名を使って Amazon Bedrock を呼び出します。
- Bedrock は指定された都道府県のお土産候補とその選ぶポイントをテキストで生成します。
- Lambda 関数は Bedrock からの応答を受け取り、API Gateway を通じてフロントエンドに返します。
- ウェブページは API からの応答を受け取り、お土産の推薦情報をユーザーに表示します。

## 使用技術・サービス

このアプリケーションは、以下の主要な AWS サービスと技術で構成されています。

- **Amazon S3**: 静的なフロントエンドファイル（HTML, CSS, JavaScript）をホストするために使用します。
- **Amazon CloudFront**: S3 からコンテンツを高速かつ安全に配信するためのコンテンツ配信ネットワーク (CDN) として使用します。
- **Amazon API Gateway**: ブラウザからバックエンド（Lambda）へのリクエストを受け付ける RESTful API エンドポイントを提供します。CORS 設定を含め、フロントエンドからのアクセスを許可します。
- **AWS Lambda**: API Gateway からのリクエストを受けて実行されるサーバーレスコンピューティングサービスです。 Bedrock との連携ロジックを記述します。
- **Amazon Bedrock**: 基盤モデル (Foundation Models) を提供するマネージドサービスです。今回はテキスト生成モデル（例: Titan Text, Claude など）を利用してお土産情報を生成します。
- **IAM (Identity and Access Management)**: AWS リソースへのアクセス権限を管理するために使用します（Lambda 実行ロールなど）。
- **CloudWatch Logs**: Lambda 関数や API Gateway の実行ログを記録し、デバッグや監視に使用します。

## アーキテクチャ概念図

![アーキテクチャ図](https://github.com/shunsukehata/aws-bedrock-app/blob/master/docs/SouvenirSurvey.drawio)

## 扱い方
このアプリケーションは、以下の CloudFront URL にアクセスすることで利用できます。

https://d1lh0vzoe9wd2k.cloudfront.net
ブラウザで上記の URL にアクセスし、表示されたフォームに都道府県名を入力して送信してください。 Bedrock が推薦するお土産候補とポイントが表示されます。
