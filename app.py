from flask import Flask, request, jsonify
import google.generativeai as genai
import os

app = Flask(__name__)
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash")

# 根路徑 GET
@app.route('/', methods=['GET'])
def index():
    return jsonify({"msg":"Dream API backend running ok"}),200

# 測試API Key GET
@app.route('/testkey', methods=['GET'])
def testkey():
    return jsonify({"msg":"Gemini key loaded"}),200

# 重點：深度解夢 POST接口
@app.route('/dream_analysis', methods=['POST'])
def dream_analysis():
    data = request.get_json()
    dream_content = data.get("dream_content","")
    simple_analysis = data.get("simple_analysis","")
    q1 = data.get("q1","")
    q2 = data.get("q2","")
    q3 = data.get("q3","")

    prompt = f"""
你係專業解夢師，根據下面資料寫深度解夢，字數300–500字，繁體中文。
夢境：{dream_content}
初步簡單解夢：{simple_analysis}
三條問題答案：
1. 旁觀者/親身參與：{q1}
2. 夢境結局：{q2}
3. 環境熟悉/陌生：{q3}

要求：結合心理學，語氣溫和，只輸出解夢正文，唔加標題。
"""
    res = model.generate_content(prompt)
    return jsonify({"deep_analysis":res.text})

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
    
