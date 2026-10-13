import sys
sys.stdout.reconfigure(encoding='utf-8')
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from pymongo import MongoClient
from datetime import datetime
import jwt

app = Flask(__name__)
CORS(app, origins=[
    "https://dreamofwisdom.com",
    "https://www.dreamofwisdom.com"
])

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
API_URL = "https://api.deepseek.com/v1/chat/completions"
MONGODB_URI = os.environ.get("MONGODB_URI")
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")

client = MongoClient(MONGODB_URI)
db = client["dreamofwisdom"]
dream_col = db["dream_records"]

def token_required(func):
    def wrapper(*args, **kwargs):
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return jsonify({"message": "缺少Bearer Token"}), 401
        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
            current_user_id = payload["user_id"]
        except jwt.ExpiredSignatureError:
            return jsonify({"message": "Token已過期"}), 401
        except Exception as e:
            return jsonify({"message": "Token無效"}), 401
        return func(current_user_id, *args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper


# 唔帶 /api 前綴
@app.route("/analyze", methods=["POST"])
def analyze_dream():
    data = request.get_json()
    dream_content = data.get("dreamContent")
    if not dream_content:
        return jsonify({"message": "請輸入夢境內容"}), 400

    messages = [
        {
            "role": "system",
            "content": "你係專業解夢師，融合四大心理學派（精神分析、榮格、認知、完形），溫和療癒，輸出清晰結構化解夢報告"
        },
        {"role": "user", "content": dream_content}
    ]
    payload = {
        "model": "deepseek-chat",
        "messages": messages,
        "temperature": 0.7
    }
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    resp = requests.post(API_URL, headers=headers, json=payload)
    if resp.status_code != 200:
        return jsonify({"message": "DeepSeek API錯誤", "detail": resp.text}), 500
    return jsonify(resp.json())


@app.route("/dream-record", methods=["POST"])
@token_required
def save_dream_record(current_user_id):
    data = request.get_json()
    record = {
        "user_id": current_user_id,
        "dreamContent": data.get("dreamContent", ""),
        "analysis": data.get("analysis", ""),
        "tags": data.get("tags", []),
        "createdAt": datetime.utcnow()
    }
    res = dream_col.insert_one(record)
    return jsonify({
        "_id": str(res.inserted_id),
        "message": "儲存成功"
    }), 201


@app.route("/dream-records", methods=["GET"])
@token_required
def get_dream_records(current_user_id):
    records = list(dream_col.find({"user_id": current_user_id}).sort("createdAt", -1))
    for r in records:
        r["_id"] = str(r["_id"])
    return jsonify(records)


@app.route("/dream-record/<record_id>", methods=["PUT"])
@token_required
def update_dream_record(current_user_id, record_id):
    from bson import ObjectId
    try:
        obj_id = ObjectId(record_id)
    except:
        return jsonify({"message": "ID格式錯誤"}),400
    data = request.get_json()
    update_data = {
        "dreamContent": data.get("dreamContent"),
        "analysis": data.get("analysis"),
        "tags": data.get("tags", []),
        "updatedAt": datetime.utcnow()
    }
    result = dream_col.update_one(
        {"_id": obj_id, "user_id": current_user_id},
        {"$set": update_data}
    )
    if result.matched_count == 0:
        return jsonify({"message": "記錄不存在或者唔屬於你"}),404
    return jsonify({"message":"更新成功"})


@app.route("/dream-record/<record_id>", methods=["DELETE"])
@token_required
def delete_dream_record(current_user_id, record_id):
    from bson import ObjectId
    try:
        obj_id = ObjectId(record_id)
    except:
        return jsonify({"message": "ID格式錯誤"}),400
    result = dream_col.delete_one({"_id": obj_id, "user_id": current_user_id})
    if result.deleted_count == 0:
        return jsonify({"message": "記錄不存在或者唔屬於你"}),404
    return jsonify({"message": "刪除成功"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
