import os
import google.generativeai as genai
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # 開啟跨域，畀React前端呼叫

# 讀取環境變數 GEMINI_API_KEY
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

@app.route("/", methods=["GET"])
def index():
    return jsonify({"status": "ok"})

# 測試API Key是否成功載入
@app.route("/testkey", methods=["GET"])
def testkey():
    if GEMINI_API_KEY:
        return jsonify({
            "has_key": True,
            "key_prefix": GEMINI_API_KEY[:5]
        })
    else:
        return jsonify({"has_key": False})

# 深度解夢接口：接收簡單解夢 + 3條問題答案，輸出300–500字深度解析
@app.route("/dream", methods=["POST"])
def dream_analysis():
    try:
        data = request.get_json()
        dream_text = data.get("dream", "")
        simple_analysis = data.get("simple_analysis", "")
        q1 = data.get("q1", "") # 旁觀者 / 親身參與
        q2 = data.get("q2", "") # 明確結局 / 突然中斷
        q3 = data.get("q3", "") # 環境熟悉 / 陌生

        if not dream_text.strip():
            return jsonify({"error": "請輸入夢境內容"}), 400

        prompt = f"""你係專業解夢師，結合心理學、象徵學做深度解夢，繁體中文，字數控制300–500字。
夢境原文：{dream_text}
初步簡單解夢：{simple_analysis}
補充問卷答案：
1. 在夢裡，你是旁觀者，還是親身參與夢中事件？答：{q1}
2. 夢境結束時，有冇出現一個明確的結局，或是夢是突然中斷？答：{q2}
3. 夢裡的環境，感覺熟悉還是完全陌生？答：{q3}

要求：
- 結合夢境同三條問卷答案一齊分析
- 拆解象徵、潛意識情緒、內心狀態
- 最後給溫和參考建議
- 嚴格控制300–500字，唔好太短或太長。"""
        res = model.generate_content(prompt)
        return jsonify({"result": res.text})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
    
