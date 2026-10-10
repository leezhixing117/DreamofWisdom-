import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests

app = Flask(__name__)
# 更新CORS，只開放正式網站（www同非www）
CORS(app, origins=[
    "https://dreamofwisdom.com",
    "https://www.dreamofwisdom.com"
])

# 讀取Gemini金鑰（Render環境變數）
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

# GET根路徑，Render健康檢查
@app.route('/', methods=['GET'])
def index():
    return "DreamWisdom API Ready"

# POST根路徑，深度解夢接口
@app.route('/', methods=['POST'])
def deep_dream():
    try:
        data = request.get_json()
        simple_analysis = data.get("simple_analysis", "")
        q1 = data.get("q1", "")
        q2 = data.get("q2", "")
        q3 = data.get("q3", "")

        prompt = f"""
你係專業解夢師，結合心理學理論做深度詳細解夢，字數嚴格控制300–500字，語氣細緻易懂，使用繁體中文。
資料：
【第一步簡單解夢內容】
{simple_analysis}
【三條補充問題回覆】
1. 你係旁觀者，定親身參與夢中事件：{q1}
2. 夢境結束時，有冇明確結局，定突然中斷：{q2}
3. 夢入面環境感覺熟悉定陌生：{q3}

要求：
1. 唔好直接重複簡單解夢原文，要做更深層次潛意識解讀
2. 著重夢入面嘅情緒、內在壓力、內心渴望、潛藏訊息
3. 邏輯順暢，行文自然，唔使用列表
4. 結尾可以給溫和嘅自我反思提示
"""
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        res = requests.post(API_URL, json=payload, timeout=30)

        # 分類處理Gemini錯誤碼
        if res.status_code == 400:
            return jsonify({
                "success": False,
                "error": "Gemini請求參數錯誤，模型/授權異常"
            }), 400
        if res.status_code == 401:
            return jsonify({
                "success": False,
                "error": "API金鑰認證失敗，請聯絡管理員"
            }), 401
        if res.status_code == 429:
            return jsonify({
                "success": False,
                "error": "今日AI配額已用盡，請稍後再試"
            }), 429

        res.raise_for_status()
        result_json = res.json()
        # 防崩檢查：確保有候選回覆
        if not result_json.get("candidates") or len(result_json["candidates"]) == 0:
            return jsonify({
                "success": False,
                "error": "Gemini冇返回有效內容"
            }), 500
            
        output_text = result_json["candidates"][0]["content"]["parts"][0]["text"]

        return jsonify({
            "success": True,
            "deep_result": output_text
        })

    except requests.exceptions.Timeout:
        return jsonify({
            "success": False,
            "error": "請求超時，網絡延遲，請重新嘗試"
        }), 504
    except Exception as err:
        return jsonify({
            "success": False,
            "error": f"伺服器錯誤：{str(err)}"
        }), 500

# 舊路由保留備用
@app.route('/dream_analysis', methods=['POST'])
def dream_analysis():
    try:
        data = request.get_json()
        dream_content = data.get("dream_content", "")
        simple_analysis = data.get("simple_analysis", "")
        q1 = data.get("q1", "")
        q2 = data.get("q2", "")
        q3 = data.get("q3", "")

        prompt = f"""
你係專業解夢師，結合心理學理論，根據以下資料寫詳細解夢，字數300–500字，繁體中文。
要求：唔好重複簡單解夢原文，深入解讀潛意識、內在情緒，行文自然唔好用列表，結尾加溫和反思提示。
夢境內容：{dream_content}
初步簡單解夢：{simple_analysis}
補充問題：
1. 你係旁觀者定親身參與：{q1}
2. 夢境結局：{q2}
3. 環境感覺：{q3}
"""
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        res = requests.post(API_URL, json=payload, timeout=30)

        if res.status_code == 400:
            return jsonify({"error": "Gemini請求參數錯誤，模型/授權異常"}), 400
        if res.status_code == 401:
            return jsonify({"error": "API金鑰認證失敗，請聯絡管理員"}), 401
        if res.status_code == 429:
            return jsonify({"error": "今日AI配額已用盡，請稍後再試"}), 429

        res.raise_for_status()
        result_json = res.json()
        if not result_json.get("candidates") or len(result_json["candidates"]) == 0:
            return jsonify({"error": "Gemini冇返回有效內容"}), 500
            
        output_text = result_json["candidates"][0]["content"]["parts"][0]["text"]

        return jsonify({"deep_analysis": output_text})

    except requests.exceptions.Timeout:
        return jsonify({"error": "請求超時，網絡延遲，請重新嘗試"}), 504
    except Exception as err:
        return jsonify({"error": str(err)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
