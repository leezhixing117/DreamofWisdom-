from flask import Flask, request, jsonify
import google.generativeai as genai
import os

app = Flask(__name__)

# 讀取環境變數 GEMINI_API_KEY
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

SYSTEM_PROMPT = """你是專業解夢師，融合精神分析、榮格、完形心理學、象徵學。全程繁體中文，文筆簡潔。只依據夢境內容詮釋，禁止搜尋外部資料。
輸出固定三段結構：
①核心象徵拆解
②潛意識情緒與內在衝突解析
③啟發性自我覺察結論
回應控制在100字以內，不作吉凶預言。"""

model = genai.GenerativeModel(
    model_name="gemini-2.0-flash",
    system_instruction=SYSTEM_PROMPT
)

@app.route("/dream", methods=["POST"])
def dream_analysis():
    data = request.get_json()
    dream_text = data.get("dream", "")
    if not dream_text:
        return jsonify({"error": "請輸入夢境內容"}),400
    res = model.generate_content(dream_text)
    return jsonify({"result": res.text})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))