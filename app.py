import sys
sys.stdout.reconfigure(encoding='utf-8')
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from pymongo import MongoClient
from datetime import datetime

app = Flask(__name__)
# CORS 維持正式域名
CORS(app, origins=[
    "https://dreamofwisdom.com",
    "https://www.dreamofwisdom.com"
])

# 讀取環境變數
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
API_URL = "https://api.deepseek.com/v1/chat/completions"
MONGODB_URI = os.environ.get("MONGODB_URI")

# 連接MongoDB
client = MongoClient(MONGODB_URI)
db = client["dreamofwisdom_db"]
dream_collection = db["dream_records"]

# GET健康檢查
@app.route('/', methods=['GET'])
def index():
    return "DreamWisdom DeepSeek API Ready"

# POST 深度解夢主接口（解夢 + 自動存入資料庫）
@app.route('/', methods=['POST'])
def deep_dream():
    try:
        data = request.get_json()
        user_id = data.get("user_id", "")
        dream_content = data.get("dream_content", "")
        simple_analysis = data.get("simple_analysis", "")
        q1 = data.get("q1", "")
        q2 = data.get("q2", "")
        q3 = data.get("q3", "")
        past_records = data.get("past_records", "暫無過往記錄")

        if not user_id:
            return jsonify({"success":False,"error":"缺少user_id"}),400

        prompt = f"""
你係一位像好友一樣陪伴嘅夢境治療同行者，語氣溫柔貼地，唔好太學術化。
參考以下全部資料去解讀呢個夢：
【夢境原文】
{dream_content}
【初步簡單解夢】
{simple_analysis}
【夢境三條問題回覆】
1. 你係旁觀者，定親身參與夢中事件：{q1}
2. 夢境結束時，有冇明確結局，定突然中斷：{q2}
3. 夢入面環境感覺熟悉定陌生：{q3}
【用戶過往解夢記錄】
{past_records}

解讀指引：
1. 優先以夢境原文作核心，結合今次夢境同過往記錄，觀察內心狀態嘅連續變化，像同行者一樣傾計式解釋。
2. 唔好直接抄寫初步解夢內容，往更深層嘅感受、內心渴望同壓力去挖掘。
3. 最後提出一項簡單、可即日執行嘅日常生活小建議，幫助用戶連接夢境同現實生活。
4. 結尾輕輕鼓勵繼續記錄夢，建立習慣，吸引用戶每日回來記夢。
5. ⚠️ 硬性規則：全文**必須使用繁體中文，絕對唔可以出現任何簡體漢字**。
6. 總字數嚴格維持300–500字，行文自然，唔使用列表。
"""
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7
        }
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        res = requests.post(API_URL, headers=headers, json=payload, timeout=30)

        if res.status_code == 400:
            return jsonify({
                "success": False,
                "error": "DeepSeek請求參數錯誤"
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
        deep_result = result_json["choices"][0]["message"]["content"]

        # 存入MongoDB
        dream_record = {
            "user_id": user_id,
            "dream_content": dream_content,
            "simple_analysis": simple_analysis,
            "q1": q1,
            "q2": q2,
            "q3": q3,
            "deep_result": deep_result,
            "created_at": datetime.utcnow()
        }
        dream_collection.insert_one(dream_record)

        return jsonify({
            "success": True,
            "deep_result": deep_result
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
        user_id = data.get("user_id", "")
        dream_content = data.get("dream_content", "")
        simple_analysis = data.get("simple_analysis", "")
        q1 = data.get("q1", "")
        q2 = data.get("q2", "")
        q3 = data.get("q3", "")
        past_records = data.get("past_records", "暫無過往記錄")

        if not user_id:
            return jsonify({"error":"缺少user_id"}),400

        prompt = f"""
你係一位像好友一樣陪伴嘅夢境治療同行者，語氣溫柔貼地，唔好太學術化。
參考以下全部資料去解讀呢個夢：
【夢境原文】
{dream_content}
【初步簡單解夢】
{simple_analysis}
【夢境三條問題回覆】
1. 你係旁觀者，定親身參與夢中事件：{q1}
2. 夢境結束時，有冇明確結局，定突然中斷：{q2}
3. 夢入面環境感覺熟悉定陌生：{q3}
【用戶過往解夢記錄】
{past_records}

解讀指引：
1. 優先以夢境原文作核心，結合今次夢境同過往記錄，觀察內心狀態嘅連續變化，像同行者一樣傾計式解釋。
2. 唔好直接抄寫初步解夢內容，往更深層嘅感受、內心渴望同壓力去挖掘。
3. 最後提出一項簡單、可即日執行嘅日常生活小建議，幫助用戶連接夢境同現實生活。
4. 結尾輕輕鼓勵繼續記錄夢，建立習慣，吸引用戶每日回來記夢。
5. ⚠️ 硬性規則：全文**必須使用繁體中文，絕對唔可以出現任何簡體漢字**。
6. 總字數嚴格維持300–500字，行文自然，唔使用列表。
"""
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7
        }
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json"
        }
        res = requests.post(API_URL, headers=headers, json=payload, timeout=30)

        if res.status_code == 400:
            return jsonify({"error": "DeepSeek請求參數錯誤"}), 400
        if res.status_code == 401:
            return jsonify({"error": "API金鑰認證失敗，請聯絡管理員"}), 401
        if res.status_code == 429:
            return jsonify({"error": "今日AI配額已用盡，請稍後再試"}), 429

        res.raise_for_status()
        result_json = res.json()
        deep_result = result_json["choices"][0]["message"]["content"]

        # 存入MongoDB
        dream_record = {
            "user_id": user_id,
            "dream_content": dream_content,
            "simple_analysis": simple_analysis,
            "q1": q1,
            "q2": q2,
            "q3": q3,
            "deep_result": deep_result,
            "created_at": datetime.utcnow()
        }
        dream_collection.insert_one(dream_record)

        return jsonify({"deep_analysis": deep_result})

    except requests.exceptions.Timeout:
        return jsonify({"error": "請求超時，網絡延遲，請重新嘗試"}), 504
    except Exception as err:
        return jsonify({"error": str(err)}), 500

# 【新接口】讀取某用戶所有夢境記錄（用於生成past_records）
@app.route('/get_dream_records', methods=['GET'])
def get_dream_records():
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"success":False,"error":"缺少user_id"}),400
    records = list(dream_collection.find({"user_id":user_id}).sort("created_at",-1))
    # 轉換ObjectId同日期為字串
    output = []
    for r in records:
        output.append({
            "dream_content": r["dream_content"],
            "deep_result": r["deep_result"],
            "created_at": r["created_at"].strftime("%Y-%m-%d %H:%M")
        })
    return jsonify({"success":True,"records":output})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
