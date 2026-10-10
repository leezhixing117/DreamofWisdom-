import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai

app = Flask(__name__)
# 只允許你前端網站存取
CORS(app, origins=["https://dreamofwisdom.onrender.com"])

# 讀取環境變數嘅 Gemini API Key
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
# 更新為可用模型 gemini-3.8-flash
model = genai.GenerativeModel('models/gemini-3.8-flash')

@app.route('/')
def index():
    return "DreamWisdom API Ready"

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
夢境內容：{dream_content}
初步簡單解夢：{simple_analysis}
補充問題：
1. 你係旁觀者定親身參與：{q1}
2. 夢境結局：{q2}
3. 環境感覺：{q3}
"""
        response = model.generate_content(prompt)
        return jsonify({"deep_analysis": response.text})

    except Exception as err:
        return jsonify({"error": str(err)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
