import os
import google.generativeai as genai
from flask import Flask, request, jsonify

app = Flask(__name__)

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

# 夢境解析接口，加上錯誤捕獲
@app.route("/dream", methods=["POST"])
def dream_analysis():
    try:
        data = request.get_json()
        dream_text = data.get("dream", "")
        if not dream_text.strip():
            return jsonify({"error": "請輸入夢境內容"}), 400

        prompt = f"""你是專業解夢師，結合心理學、象徵學解析下面這個夢，使用繁體中文。
夢境內容：{dream_text}
解夢要求：
1. 簡潔分點說明夢境象徵
2. 解釋背後潛意識含義
3. 給予簡單的參考建議
不要過度冗長。"""
        res = model.generate_content(prompt)
        return jsonify({"result": res.text})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
