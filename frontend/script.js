// script.js の例

// ★ ここに、タスク8で取得したAPI Gatewayの呼び出しURLを設定します ★
const API_GATEWAY_URL = 'https://9zc6yum2x6.execute-api.ap-northeast-1.amazonaws.com/dev/consult-souvenir';

const consultForm = document.getElementById('consult-form');
const prefectureInput = document.getElementById('prefecture');
const resultDiv = document.getElementById('result');
const loadingDiv = document.getElementById('loading');
const submitButton = consultForm.querySelector('button[type="submit"]'); // 送信ボタンを取得

// フォームの送信イベントをリッスン
consultForm.addEventListener('submit', async (event) => {
    // デフォルトのフォーム送信（ページの再読み込み）をキャンセル
    event.preventDefault();

    const prefectureName = prefectureInput.value.trim(); // 入力値を取得し、前後の空白を除去

    if (!prefectureName) {
        alert('都道府県名を入力してください。');
        return; // 都道府県名が空の場合は処理を終了
    }

    // 結果表示エリアとローディング表示をリセット
    resultDiv.textContent = '';
    loadingDiv.style.display = 'block'; // ローディング表示を開始
    submitButton.disabled = true; // ボタンを無効化して連打を防ぐ

    try {
        // API GatewayのエンドポイントにPOSTリクエストを送信
        const response = await fetch(API_GATEWAY_URL, {
            method: 'POST', // HTTPメソッドはPOST
            headers: {
                'Content-Type': 'application/json' // リクエストボディの形式はJSON
            },
            // リクエストボディとして、都道府県名をJSON文字列にして送信
            body: JSON.stringify({ prefecture: prefectureName })
        });

        // HTTPステータスコードが200以外の場合はエラーとして処理
        if (!response.ok) {
            const errorData = await response.json(); // エラー応答のボディを取得（JSONと想定）
            throw new Error(`API error: ${response.status} ${response.statusText} - ${errorData.message || 'Unknown error'}`);
        }

        // 応答ボディをJSONとしてパース
        const data = await response.json();

        // パースしたデータから Bedrock の応答テキストを取得し、結果表示エリアにセット
        // Lambdaの応答JSON形式: {"prefecture": "...", "recommendation": "..."} を想定
        const recommendationText = data.recommendation || 'Bedrockからの応答がありませんでした。';
        resultDiv.textContent = recommendationText; // 結果を表示

    } catch (error) {
        // エラーが発生した場合の処理
        console.error('Fetch error:', error);
        resultDiv.textContent = 'エラーが発生しました。 Bedrock からの応答を取得できませんでした。\n' + error.message; // エラーメッセージを表示
        resultDiv.style.color = 'red'; // エラーは赤文字にするなど視覚的に区別
    } finally {
        // 処理が完了したら、ローディング表示を終了し、ボタンを有効化
        loadingDiv.style.display = 'none';
        submitButton.disabled = false;
    }
});