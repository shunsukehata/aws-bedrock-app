import json
import boto3
import logging
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS Bedrock コンソールの「Model access」で確認し、利用可能になっているモデルのIDを指定
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "amazon.titan-text-express-v1")

# AWSアカウントでBedrockが有効になっているリージョンを指定
BEDROCK_REGION = os.environ.get("BEDROCK_REGION", "ap-northeast-1")

# CloudFrontドメインや '*' を指定
ALLOWED_ORIGIN = os.environ.get("ALLOWED_ORIGIN", "*")


# Bedrock Runtime クライアントは Lambda 実行環境内で再利用されるようにグローバルに作成
try:
    bedrock_runtime = boto3.client('bedrock-runtime', region_name=BEDROCK_REGION)
    logger.info(f"Bedrock runtime client created for region: {BEDROCK_REGION}")
except Exception as e:
    logger.error(f"Failed to create Bedrock runtime client: {e}", exc_info=True)
    # クライアント作成に失敗した場合、後続のlambda_handlerでエラーを返す必要がある

def lambda_handler(event, context):
    """
    API Gatewayからのイベントを処理し、Bedrockを呼び出すLambda関数
    """
    logger.info(f"Received event: {event}")

    # API Gateway プロキシ統合の標準的な応答形式の基本構造
    api_gateway_response = {
        'statusCode': 500, # デフォルトはエラー
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': ALLOWED_ORIGIN
        },
        'body': json.dumps({ 'message': 'An unknown error occurred' }) # デフォルトのエラーメッセージ
    }

    # --- 1. API Gatewayからのイベントデータを受け取る ---
    # API Gatewayプロキシ統合の場合、リクエストボディは event['body'] に文字列として含まれる
    # JSON形式のボディを想定し、パースする
    request_body_dict = {}
    try:
        # event['body'] が文字列でない場合やJSON形式でない場合を考慮
        if isinstance(event.get('body'), str):
             # UTF-8 エンコーディングを考慮してJSON文字列をパース ★修正点★
             request_body_dict = json.loads(event['body'])
        elif event.get('body') is not None:
             # 文字列以外のボディが渡された場合（稀）
             request_body_dict = event.get('body')
             logger.warning(f"Event body is not a string. Proceeding with raw body: {request_body_dict}")
        else:
             # ボディがない場合
             logger.warning("Event body is missing.")


    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode JSON body: {e}")
        api_gateway_response['statusCode'] = 400
        api_gateway_response['body'] = json.dumps({ 'message': 'Invalid JSON body', 'error': str(e) })
        return api_gateway_response # エラー応答を返す

    except Exception as e:
        logger.error(f"Error processing event body: {e}", exc_info=True)
        api_gateway_response['statusCode'] = 500
        api_gateway_response['body'] = json.dumps({ 'message': 'Internal server error processing request body', 'error': str(e) })
        return api_gateway_response # エラー応答を返す


    # --- 2. 受け取ったデータから都道府県名を取得 ---
    # フロントエンドから送られてくるJSONボディに 'prefecture' キーがあると想定
    prefecture_name = request_body_dict.get('prefecture', None)

    if not prefecture_name or not isinstance(prefecture_name, str):
        logger.error(f"Invalid or missing prefecture name in the request body: {prefecture_name}")
        api_gateway_response['statusCode'] = 400
        api_gateway_response['body'] = json.dumps({ 'message': 'Prefecture name is required and must be a string' })
        return api_gateway_response # エラー応答を返す


    logger.info(f"Processing request for prefecture: {prefecture_name}")

    # --- 3. Bedrockへのプロンプト文字列を生成 ---
    # ユーザー入力を含むプロンプトを作成
    prompt = f"{prefecture_name}県の代表的なお土産候補と、お土産を選ぶ際のポイントを3つ程度、分かりやすく具体的に教えてください。箇条書きでお願いします。"

    # Bedrockモデルによっては、特定のプロンプト形式が推奨される場合があります。
    bedrock_request_body_dict = None # Bedrockに送信するリクエストボディ（辞書形式）

    # モデルIDに基づいてリクエストボディの形式を決定
    if BEDROCK_MODEL_ID.startswith("anthropic.claude-"):
        # Claude 3 のリクエストボディ形式
        bedrock_request_body_dict = {
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1000, # 生成するトークン数の上限を調整
            "temperature": 0.7, # 生成の多様性を調整 (0.0 - 1.0)
            "anthropic_version": "bedrock-2023-05-31"
        }
        logger.info(f"Using Claude 3 request format for model: {BEDROCK_MODEL_ID}")

    elif BEDROCK_MODEL_ID.startswith("amazon.titan-text-"):
        # Titan Text のリクエストボディ形式
        bedrock_request_body_dict = {
            "inputText": prompt,
            "textGenerationConfig": {
                "maxTokenCount": 500, # 生成するトークン数の上限を調整
                "temperature": 0.7, # 生成の多様性を調整 (0.0 - 1.0)
                "topP": 0.9 # 生成のランダム性を調整
            }
        }
        logger.info(f"Using Titan Text request format for model: {BEDROCK_MODEL_ID}")

    else:
        # サポートされていないモデルIDの場合
        logger.error(f"Unsupported Bedrock model ID format: {BEDROCK_MODEL_ID}")
        api_gateway_response['statusCode'] = 500
        api_gateway_response['body'] = json.dumps({ 'message': 'Unsupported Bedrock model ID configured', 'modelId': BEDROCK_MODEL_ID })
        return api_gateway_response # エラー応答を返す

    if bedrock_request_body_dict is None:
         # ここに来ることはないはずですが念のため
         logger.error("Bedrock request body was not generated.")
         api_gateway_response['statusCode'] = 500
         api_gateway_response['body'] = json.dumps({ 'message': 'Failed to prepare Bedrock request body' })
         return api_gateway_response


    logger.info(f"Generated prompt: {prompt}")
    # ログに Bedrock リクエストボディ全体を出力すると機密情報を含む可能性があるため注意
    # logger.info(f"Bedrock request body dict: {bedrock_request_body_dict}")


    # --- 4. Boto3を使ってBedrock APIを呼び出す ---
    try:
        # Bedrock Runtime クライアントが正しく作成されているか確認
        if 'bedrock_runtime' not in globals() or bedrock_runtime is None:
             raise Exception("Bedrock runtime client is not initialized.")

        # リクエストボディを JSON 文字列に変換し、UTF-8 バイト列にエンコード
        request_body_bedrock_bytes = json.dumps(bedrock_request_body_dict).encode('utf-8')

        logger.info(f"Invoking model: {BEDROCK_MODEL_ID}")

        # invoke_model を呼び出す
        response = bedrock_runtime.invoke_model(
            modelId=BEDROCK_MODEL_ID,
            contentType="application/json",
            accept="application/json",
            body=request_body_bedrock_bytes # ★ UTF-8 バイト列を渡す ★
        )

        # --- 5. Bedrockからの応答をパース ---
        # 応答ボディを読み込み、UTF-8でデコードしてJSONパース
        response_body_bytes = response['body'].read()
        response_body_string = response_body_bytes.decode('utf-8')
        response_body_dict = json.loads(response_body_string)

        logger.info(f"Received raw Bedrock response: {response_body_string}")

        # モデル別の応答パース処理 ★修正点：モデルごとの応答パースを明確化★
        generated_text = "Bedrockからの応答をパースできませんでした。" # デフォルト値

        if BEDROCK_MODEL_ID.startswith("anthropic.claude-"):
             # Claude 3 の応答例: {"content":[{"text":"...","type":"text"}], ...}
             content_list = response_body_dict.get('content', [])
             sb = []
             for content_item in content_list:
                 if isinstance(content_item, dict) and content_item.get('type') == 'text':
                     sb.append(content_item.get('text', ''))
             generated_text = "".join(sb)
             logger.info("Parsed Claude 3 response.")

        elif BEDROCK_MODEL_ID.startswith("amazon.titan-text-"):
             # Titan Text の応答例: {"results":[{"outputText":"...", ...}], ...}
             results_list = response_body_dict.get('results', [])
             if results_list and isinstance(results_list[0], dict):
                 generated_text = results_list[0].get('outputText', generated_text)
             logger.info("Parsed Titan Text response.")

        elif BEDROCK_MODEL_ID.startswith("meta.llama"): # 例: Llama 2
             # Llama 2 の応答例: {"generation":"...", ...}
             generated_text = response_body_dict.get('generation', generated_text)
             logger.info("Parsed Llama response.")

        else:
            logger.warning(f"Parsing not implemented for model ID: {BEDROCK_MODEL_ID}. Raw response: {response_body_string}")
            generated_text = f"応答のパースが未対応のモデルです ({BEDROCK_MODEL_ID}). Raw Response: {response_body_string[:200]}..." # 生の応答の一部を表示

        if not generated_text: # パース結果が空文字列だった場合など
             generated_text = "Bedrockからの応答はありましたが、テキストを抽出できませんでした。"


        logger.info(f"Generated text: {generated_text[:100]}...") # 生成されたテキストの冒頭をログ出力

    except Exception as e:
        # Bedrock API 呼び出しや応答パース中にエラーが発生した場合
        logger.error(f"Error during Bedrock API call or response parsing: {e}", exc_info=True)
        # ★ エラー応答のstatusCodeとbodyを設定し、headersは既に設定済み ★
        api_gateway_response['statusCode'] = 500
        api_gateway_response['body'] = json.dumps({
            'message': 'Error processing Bedrock API response',
            'error': str(e),
            'modelId': BEDROCK_MODEL_ID
        })
        return api_gateway_response # エラー応答を返す


    # --- 6. API Gatewayに返すための成功応答データを作成 ---
    api_gateway_response['statusCode'] = 200
    # headers は関数の最初で設定済み ('Access-Control-Allow-Origin' 含む)
    api_gateway_response['body'] = json.dumps({
        'prefecture': prefecture_name,
        'recommendation': generated_text
    })

    logger.info("Lambda execution completed successfully.")
    return api_gateway_response # 成功応答を返す