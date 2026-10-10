import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai

app = Flask(__name__)
# 設定只允許你個網站域名訪問（安全版，替換成你前端網址）
CORS(app, origins=["https://dreamofwisdom.onrender.com"])

try:
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])
    model = genai.GenerativeModel('gemini-2.0-flash')
except Exception as e:
    print(f"初始化失敗: {str(e)}")

@app.route('/')
def index():
    return "DreamWisdom API Ready"

@app.route('/dream_analysis', methods=['POST'])
def dream_analysis():
    try:
        data = request.get_json()
        dream_content = data.get("dream_content","")
        simple_analysis = data.get("simple_analysis","")
        q1 = data.get("q1","")
        q2 = data.get("q2","")
        q3 = data.get("q3","")

        prompt = f"""
你係專業解夢師，結合心理學做詳細解夢，字數300–500字，繁體中文。
夢境內容：{dream_content}
初步簡單解夢：{simple_analysis}
補充問題：
1. 你係旁觀者，定親身參與夢中事件？答：{q1}
2. 夢境完結時，有冇明確結局，定係突然中斷？答：{q2}
3. 夢入面環境，感覺熟悉定完全陌生？答：{q3}
"""
        response = model.generate_content(prompt)
        return jsonify({"deep_analysis": response.text})
    except Exception as err:
        return jsonify({"error": str(err)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
