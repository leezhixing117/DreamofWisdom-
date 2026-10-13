import sys
sys.stdout.reconfigure(encoding='utf-8')
import os
import jwt
import bcrypt
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from pymongo import MongoClient
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText

app = Flask(__name__)

# CORS 允許你哋網站域名
CORS(app, origins=[
    "https://dreamofwisdom.com",
    "https://www.dreamofwisdom.com"
])

# 讀環境變數
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
API_URL = "https://api.deepseek.com/v1/chat/completions"
MONGODB_URI = os.environ.get("MONGODB_URI")
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
EMAIL_SENDER = os.environ.get("EMAIL_SENDER")
EMAIL_PASS = os.environ.get("EMAIL_PASS")
FRONTEND_URL = os.environ.get("FRONTEND_URL")

# 連 MongoDB
client = MongoClient(MONGODB_URI)
db = client["dreamofwisdom"]
users_col = db["users"]
dream_records_col = db["dream_records"]

# JWT Token 驗證函數
def verify_token():
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None
    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        return payload["user_id"]
    except Exception:
        return None

# --------------------------
# 1. 解夢接口 /analyze
# --------------------------
@app.route("/analyze", methods=["POST"])
def analyze_dream():
    data = request.get_json()
    dream_content = data.get("dream")
    if not dream_content:
        return jsonify({"message": "請輸入夢境內容"}), 400

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "你係專業解夢師，結合心理學解讀夢境，回覆溫和有啟發性。"},
            {"role": "user", "content": dream_content}
        ],
        "temperature": 0.7
    }
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    res = requests.post(API_URL, json=payload, headers=headers)
    if res.status_code != 200:
        return jsonify({"message": "AI解夢服務失敗"}), 500
    result = res.json()
    reply = result["choices"][0]["message"]["content"]
    return jsonify({"analysis": reply})

# --------------------------
# 2. 註冊 /auth/register
# --------------------------
@app.route("/auth/register", methods=["POST"])
def register():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    if not email or not password:
        return jsonify({"message": "電郵同密碼唔可以空"}), 400

    exist = users_col.find_one({"email": email})
    if exist:
        return jsonify({"message": "呢個電郵已經註冊咗"}), 400

    hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    user_doc = {
        "email": email,
        "password": hashed_pw,
        "created_at": datetime.utcnow()
    }
    insert_result = users_col.insert_one(user_doc)
    user_id = str(insert_result.inserted_id)

    token = jwt.encode(
        {"user_id": user_id, "exp": datetime.utcnow() + timedelta(days=7)},
        JWT_SECRET_KEY,
        algorithm="HS256"
    )
    return jsonify({
        "message": "註冊成功",
        "token": token,
        "user_id": user_id
    }), 201

# --------------------------
# 3. 登入 /auth/login
# --------------------------
@app.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    if not email or not password:
        return jsonify({"message": "電郵同密碼唔可以空"}), 400

    user = users_col.find_one({"email": email})
    if not user:
        return jsonify({"message": "帳號不存在"}), 401
    if not bcrypt.checkpw(password.encode("utf-8"), user["password"]):
        return jsonify({"message": "密碼錯誤"}), 401

    user_id = str(user["_id"])
    token = jwt.encode(
        {"user_id": user_id, "exp": datetime.utcnow() + timedelta(days=7)},
        JWT_SECRET_KEY,
        algorithm="HS256"
    )
    return jsonify({
        "message": "登入成功",
        "token": token,
        "user_id": user_id
    })

# --------------------------
# 4. 儲存夢境紀錄 /dream-record
# --------------------------
@app.route("/dream-record", methods=["POST"])
def save_dream_record():
    user_id = verify_token()
    if not user_id:
        return jsonify({"message": "未登入"}), 401
    data = request.get_json()
    data["user_id"] = user_id
    data["created_at"] = datetime.utcnow()
    insert_result = dream_records_col.insert_one(data)
    return jsonify({
        "message": "儲存成功",
        "record_id": str(insert_result.inserted_id)
    }), 201

# --------------------------
# 5. 讀取用戶所有夢境 /dream-record
# --------------------------
@app.route("/dream-record", methods=["GET"])
def get_dream_records():
    user_id = verify_token()
    if not user_id:
        return jsonify({"message": "未登入"}), 401
    records = list(dream_records_col.find({"user_id": user_id}).sort("created_at", -1))
    for r in records:
        r["_id"] = str(r["_id"])
    return jsonify(records)

# --------------------------
# 6. 刪除單條夢境 DELETE /dream-record/<record_id>
# --------------------------
from bson import ObjectId
@app.route("/dream-record/<record_id>", methods=["DELETE"])
def delete_dream_record(record_id):
    user_id = verify_token()
    if not user_id:
        return jsonify({"message": "未登入"}), 401
    try:
        result = dream_records_col.delete_one({"_id": ObjectId(record_id), "user_id": user_id})
    except:
        return jsonify({"message": "記錄ID錯誤"}), 400
    if result.deleted_count == 0:
        return jsonify({"message": "搵唔到呢條紀錄"}), 404
    return jsonify({"message": "刪除成功"})

# --------------------------
# 7. 更新夢境標籤 PUT /dream-record/<record_id>
# --------------------------
@app.route("/dream-record/<record_id>", methods=["PUT"])
def update_dream_tags(record_id):
    user_id = verify_token()
    if not user_id:
        return jsonify({"message": "未登入"}), 401
    data = request.get_json()
    tags = data.get("tags", [])
    try:
        result = dream_records_col.update_one(
            {"_id": ObjectId(record_id), "user_id": user_id},
            {"$set": {"tags": tags}}
        )
    except:
        return jsonify({"message": "記錄ID錯誤"}), 400
    if result.matched_count == 0:
        return jsonify({"message": "搵唔到呢條紀錄"}), 404
    return jsonify({"message": "標籤更新成功"})

# --------------------------
# 忘記密碼、發送重設連結
# --------------------------
@app.route("/auth/forgot-password", methods=["POST"])
def forgot_password():
    data = request.get_json()
    email = data.get("email")
    user = users_col.find_one({"email": email})
    if not user:
        return jsonify({"message": "如果電郵存在，重設連結已發送"}), 200
    user_id = str(user["_id"])
    reset_token = jwt.encode(
        {"user_id": user_id, "exp": datetime.utcnow() + timedelta(hours=1)},
        JWT_SECRET_KEY,
        algorithm="HS256"
    )
    reset_link = f"{FRONTEND_URL}/reset-password?token={reset_token}"
    msg = MIMEText(f"點擊連結重設密碼：{reset_link}", "plain", "utf-8")
    msg["Subject"] = "夢境智慧 - 重設密碼"
    msg["From"] = EMAIL_SENDER
    msg["To"] = email
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASS)
        server.send_message(msg)
        server.quit()
    except Exception as e:
        print("send email error:", e)
        return jsonify({"message": "郵件發送失敗"}), 500
    return jsonify({"message": "如果電郵存在，重設連結已發送"}), 200

# --------------------------
# 重設密碼
# --------------------------
@app.route("/auth/reset-password", methods=["POST"])
def reset_password():
    data = request.get_json()
    token = data.get("token")
    new_pw = data.get("password")
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        user_id = payload["user_id"]
    except Exception:
        return jsonify({"message": "連結無效或者已過期"}), 400
    hashed_pw = bcrypt.hashpw(new_pw.encode("utf-8"), bcrypt.gensalt())
    users_col.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"password": hashed_pw}}
    )
    return jsonify({"message": "密碼重設成功，可以登入"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
