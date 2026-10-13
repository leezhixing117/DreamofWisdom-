import sys
sys.stdout.reconfigure(encoding='utf-8')
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from pymongo import MongoClient
from datetime import datetime
import jwt
import bcrypt
import smtplib
from email.mime.text import MIMEText
from bson import ObjectId

app = Flask(__name__)
# ========== CORS設定 ==========
CORS(app,
     origins=[
         "https://dreamofwisdom.com",
         "https://www.dreamofwisdom.com"
     ],
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
)

# 環境變數【重點修正：MAIL_PASS，對齊Render入面嘅key名】
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
API_URL = "https://api.deepseek.com/v1/chat/completions"
MONGODB_URI = os.environ.get("MONGODB_URI")
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
EMAIL_SENDER = os.environ.get("EMAIL_SENDER")
EMAIL_PASS = os.environ.get("MAIL_PASS")

# MongoDB連接
client = MongoClient(MONGODB_URI)
db = client["dreamofwisdom"]
dream_col = db["dream_records"]
user_col = db["users"]
verify_col = db["verify_codes"]

# JWT 驗證裝飾器
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

# 發送驗證碼郵件函數
def send_email(to_email, code):
    msg = MIMEText(f"你的DreamOfWisdom驗證碼：{code}\n有效期15分鐘", "plain", "utf-8")
    msg["Subject"] = "DreamOfWisdom 驗證碼"
    msg["From"] = EMAIL_SENDER
    msg["To"] = to_email
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_SENDER, EMAIL_PASS)
        server.send_message(msg)

# ========== 原有解夢 & 夢境紀錄接口（全部加 /api） ==========
@app.route("/api/analyze", methods=["POST"])
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


@app.route("/api/dream-record", methods=["POST"])
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


@app.route("/api/dream-records", methods=["GET"])
@token_required
def get_dream_records(current_user_id):
    records = list(dream_col.find({"user_id": current_user_id}).sort("createdAt", -1))
    for r in records:
        r["_id"] = str(r["_id"])
    return jsonify(records)


@app.route("/api/dream-record/<record_id>", methods=["PUT"])
@token_required
def update_dream_record(current_user_id, record_id):
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


@app.route("/api/dream-record/<record_id>", methods=["DELETE"])
@token_required
def delete_dream_record(current_user_id, record_id):
    try:
        obj_id = ObjectId(record_id)
    except:
        return jsonify({"message": "ID格式錯誤"}),400
    result = dream_col.delete_one({"_id": obj_id, "user_id": current_user_id})
    if result.deleted_count == 0:
        return jsonify({"message": "記錄不存在或者唔屬於你"}),404
    return jsonify({"message": "刪除成功"})

# ========== 全套Auth註冊登入接口（全部加 /api） ==========
@app.route("/api/send-register-code", methods=["POST"])
def send_register_code():
    data = request.get_json()
    email = data.get("email","").strip().lower()
    password = data.get("password","")
    if not email or len(password) < 6:
        return jsonify({"message":"電郵必填，密碼最少6位"}),400
    # 檢查用戶是否已存在
    if user_col.find_one({"email":email}):
        return jsonify({"message":"此電郵已經註冊"}),400
    # 生成6位驗證碼
    import random
    code = str(random.randint(100000,999999))
    expire = datetime.utcnow().timestamp() + 15*60
    # 覆蓋舊驗證碼
    verify_col.delete_many({"email":email, "type":"register"})
    verify_col.insert_one({
        "email":email, "code":code, "expire":expire, "type":"register",
        "password":password
    })
    try:
        send_email(email, code)
    except Exception as e:
        print("send mail error", str(e))
        return jsonify({"message":"發送電郵失敗，檢查SMTP設定"}),500
    return jsonify({"message":"驗證碼已發送到你的電郵"})


@app.route("/api/verify-register", methods=["POST"])
def verify_register():
    data = request.get_json()
    email = data.get("email","").strip().lower()
    code = data.get("code","").strip()
    item = verify_col.find_one({"email":email, "code":code, "type":"register"})
    if not item or datetime.utcnow().timestamp() > item["expire"]:
        return jsonify({"message":"驗證碼無效或已過期"}),400
    # 加密密碼存入users
    hash_pw = bcrypt.hashpw(item["password"].encode("utf-8"), bcrypt.gensalt())
    user_col.insert_one({
        "email":email,
        "password_hash":hash_pw,
        "star_coins":6,
        "createdAt":datetime.utcnow()
    })
    verify_col.delete_one({"_id":item["_id"]})
    return jsonify({"message":"註冊成功，可以登入"})


@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email","").strip().lower()
    password = data.get("password","")
    user = user_col.find_one({"email":email})
    if not user:
        return jsonify({"message":"電郵或密碼錯誤"}),401
    if not bcrypt.checkpw(password.encode("utf-8"), user["password_hash"]):
        return jsonify({"message":"電郵或密碼錯誤"}),401
    token = jwt.encode(
        {"user_id":str(user["_id"]), "email":user["email"]},
        JWT_SECRET_KEY,
        algorithm="HS256"
    )
    return jsonify({
        "token":token,
        "email":user["email"],
        "star_coins":user.get("star_coins",0),
        "message":"登入成功"
    })


@app.route("/api/me", methods=["GET"])
@token_required
def get_me(current_user_id):
    try:
        u = user_col.find_one({"_id":ObjectId(current_user_id)}, {"password_hash":0})
    except:
        return jsonify({"message":"用戶不存在"}),404
    if not u:
        return jsonify({"message":"用戶不存在"}),404
    u["_id"] = str(u["_id"])
    return jsonify(u)


@app.route("/api/send-reset-code", methods=["POST"])
def send_reset_code():
    data = request.get_json()
    email = data.get("email","").strip().lower()
    user = user_col.find_one({"email":email})
    if not user:
        return jsonify({"message":"該電郵未有註冊"}),400
    import random
    code = str(random.randint(100000,999999))
    expire = datetime.utcnow().timestamp() + 15*60
    verify_col.delete_many({"email":email, "type":"reset"})
    verify_col.insert_one({"email":email,"code":code,"expire":expire,"type":"reset"})
    try:
        send_email(email, code)
    except Exception as e:
        print("reset mail error", str(e))
        return jsonify({"message":"發送電郵失敗"}),500
    return jsonify({"message":"重設密碼驗證碼已發送"})


@app.route("/api/reset-password", methods=["POST"])
def reset_password():
    data = request.get_json()
    email = data.get("email","").strip().lower()
    code = data.get("code","").strip()
    new_pw = data.get("newPassword","")
    if len(new_pw) <6:
        return jsonify({"message":"密碼最少6位"}),400
    item = verify_col.find_one({"email":email,"code":code,"type":"reset"})
    if not item or datetime.utcnow().timestamp()>item["expire"]:
        return jsonify({"message":"驗證碼無效或過期"}),400
    hash_pw = bcrypt.hashpw(new_pw.encode("utf-8"), bcrypt.gensalt())
    user_col.update_one({"email":email}, {"$set":{"password_hash":hash_pw}})
    verify_col.delete_one({"_id":item["_id"]})
    return jsonify({"message":"密碼重設成功"})


# 測試SMTP郵件接口
@app.route("/api/test-email", methods=["GET"])
def test_email():
    try:
        send_email(EMAIL_SENDER, "123456")
        return jsonify({"ok":True, "message":"測試郵件已送出"})
    except Exception as e:
        return jsonify({"ok":False, "error":str(e)}),500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
