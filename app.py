from flask import Flask, request, jsonify
import google.generativeai as genai
import os

app = Flask(__name__)
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

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
根據資料做深度解夢，300-500字，繁體中文。
夢境：{dream_content}
初步解夢：{simple_analysis}
問題1：{q1}
問題2：{q2}
問題3：{q3}
"""
        model = genai.GenerativeModel("gemini-1.5-flash")
        res = model.generate_content(prompt)
        return jsonify({"deep_analysis": res.text})
    except Exception as e:
        return jsonify({"error": str(e)}),500

@app.route('/', methods=['GET'])
def index():
    return "API 正常運行"

if __name__ == "__main__":
    app.run(host="0.0.0.0")
    
