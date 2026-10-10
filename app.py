from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
import os

app = Flask(__name__)
CORS(app)

# 讀取Render環境變數入面嘅Gemini金鑰
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

@app.route('/dream_analysis', methods=['POST'])
def dream_analysis():
    try:
        json_data = request.get_json()
        dream_content = json_data.get("dream_content", "")
        simple_analysis = json_data.get("simple_analysis", "")
        q1 = json_data.get("q1", "")
        q2 = json_data.get("q2", "")
        q3 = json_data.get("q3", "")

        prompt = f"""
你係專業解夢師，根據下面資料撰寫深度解夢，繁體中文，字數300至500字。
夢境內容：{dream_content}
初步簡單解夢：{simple_analysis}
問題1（旁觀者/親身參與）：{q1}
問題2（結局：明確結局 / 突然中斷）：{q2}
問題3（環境：熟悉 / 陌生）：{q3}

要求：
- 結合心理學角度，邏輯連貫
- 控制字數300–500字
- 只輸出解夢正文，唔加標題、唔加前言、唔加備註
"""
        model = genai.GenerativeModel("gemini-1.5-flash")
        response = model.generate_content(prompt)
        return jsonify({"deep_analysis": response.text})

    except Exception as err:
        return jsonify({"error": str(err)}), 500

# 健康檢查路由，Render用來確認服務正常
@app.route('/', methods=['GET'])
def health_check():
    return "DreamWisdom API Ready", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0")
    
