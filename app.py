import sys
sys.stdout.reconfigure(encoding='utf-8')
import os
import jwt
import uuid
import random
import smtplib
from email.mime.text import MIMEText
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from pymongo import MongoClient
from datetime import datetime, timedelta

app = Flask(__name__)
# ✅ 加上 supports_credentials=True 解決OPTIONS preflight攔截
CORS(app, origins=[
    "https://dreamofwisdom.com",
    "https://www.dreamofwisdom.com"
], supports_credentials=True)

# 讀取環境變數
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
API_URL = "https://api.deepseek.com/v1/chat/completions"
MONGODB_URI = os.environ.get("MONGODB_URI")
JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")

# SMTP 郵件設定
EMAIL_SENDER = os.environ.get("EMAIL_SENDER")
EMAIL_PASS = os.environ.get("EMAIL_PASS")
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465

# 連接MongoDB
client = MongoClient(MONGODB_URI)
db = client["dreamofwisdom_db"]
dream_collection = db["dream_records"]
user_collection = db["members"]
verify_collection = db["email_verify_codes"]

# GET健康檢查
@app.route('/', methods=['GET'])
def index():
    return "DreamWisdom API Ready"

# POST /analyze 主解夢接口
@app.route('/analyze', methods=['POST'])
def deepseek_analyze():
    try:
        payload = request.get_json()
        dream_content = payload.get("dream_content")
        if not dream_content:
            return jsonify({"success":False, "message":"請輸入夢境內容"}),400

        messages = [
            {"role":"user", "content": dream_content}
        ]
        reqBody = {
            "model": "deepseek-chat",
            "messages": messages,
            "temperature":0.7
        }
        headers = {
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type":"application/json"
        }
        res = requests.post(API_URL, headers=headers, json=reqBody, timeout=60)
        if res.status_code !=200:
            return jsonify({"success":False, "message":"AI解夢服務錯誤"}),500
        aiResult = res.json()
        reply = aiResult["choices"][0]["message"]["content"]
        return jsonify({"success":True, "result":reply})
    except Exception as err:
        print("解夢錯誤：",str(err))
        return jsonify({"success":False, "message":"伺服器錯誤"}),500

# POST /deep-analyze 深度解夢
@app.route('/deep-analyze', methods=['POST'])
def deep_analyze():
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"success": False, "message": "未登入"}), 401
    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        return jsonify({"success": False, "message": "憑證無效"}), 401
    data = request.get_json()
    dream_content = data.get("dream_content")
    if not dream_content:
        return jsonify({"success":False, "message":"缺少夢境內容"}),400
    messages = [
        {"role":"system","content":"你係專業解夢師，結合心理學深度解析夢境"},
        {"role":"user", "content": dream_content}
    ]
    reqBody = {
        "model": "deepseek-chat",
        "messages": messages,
        "temperature":0.7
    }
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type":"application/json"
    }
    res = requests.post(API_URL, headers=headers, json=reqBody, timeout=60)
    if res.status_code !=200:
        return jsonify({"success":False, "message":"深度解夢失敗"}),500
    aiResult = res.json()
    reply = aiResult["choices"][0]["message"]["content"]
    return jsonify({"success":True, "result":reply})

# POST /quiz-finish 問卷提交
@app.route('/quiz-finish', methods=['POST'])
def quiz_finish():
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"success": False, "message": "未登入"}), 401
    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        user_id = payload["userId"]
    except jwt.InvalidTokenError:
        return jsonify({"success": False, "message": "憑證無效"}), 401
    user_collection.update_one({"user_id":user_id}, {"$inc":{"star_coins":3}})
    return jsonify({"success":True, "message":"問卷提交成功，已發放星星"}),200

# POST /watch-ad 看廣告拿星
@app.route('/watch-ad', methods=['POST'])
def watch_ad():
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"success": False, "message": "未登入"}), 401
    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        user_id = payload["userId"]
    except jwt.InvalidTokenError:
        return jsonify({"success": False, "message": "憑證無效"}), 401
    user = user_collection.find_one({"user_id":user_id})
    count = user.get("adWatchCount",0) + 1
    if count >=3:
        user_collection.update_one({"user_id":user_id}, {"$inc":{"star_coins":3}, "$set":{"adWatchCount":0}})
        return jsonify({"success":True, "message":"已累計3個廣告，兌換3星星！"}),200
    else:
        user_collection.update_one({"user_id":user_id}, {"$set":{"adWatchCount":count}})
        return jsonify({"success":True, "message":f"已觀看{count}/3個廣告"}),200

# GET /me 取得用戶資料
@app.route('/me', methods=['GET'])
def get_profile():
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"success": False, "message": "未登入"}), 401
    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        user_id = payload["userId"]
    except jwt.InvalidTokenError:
        return jsonify({"success": False, "message": "憑證無效"}), 401
    user = user_collection.find_one({"user_id":user_id})
    if not user:
        return jsonify({"success":False,"message":"找不到用戶"}),404
    return jsonify({
        "success":True,
        "user":{
            "user_id": user["user_id"],
            "email": user["email"],
            "star_coins": user["star_coins"],
            "adWatchCount": user.get("adWatchCount",0)
        }
    })

# 舊解夢路由，向後兼容唔刪
@app.route('/', methods=['POST'])
def deep_dream_old():
    return deepseek_analyze()

# 舊接口：讀取夢境紀錄（向後兼容）
@app.route('/get_dream_records', methods=['GET'])
def get_dream_records():
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"success":False,"error":"缺少user_id"}),400
    records = list(dream_collection.find({"user_id":user_id}).sort("created_at",-1))
    for item in records:
        item["_id"] = str(item["_id"])
    return jsonify({"success":True,"records":records})


# ============ 夢境 CRUD API（JWT登入驗證）============
# POST /dream-record 新增夢境紀錄
@app.route('/dream-record', methods=['POST'])
def save_dream_record():
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"success": False, "message": "未提供登入憑證"}), 401
    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        user_id = payload["userId"]
    except jwt.InvalidTokenError:
        return jsonify({"success": False, "message": "憑證無效或已過期"}), 401

    data = request.get_json()
    dream_id = f"dream_{uuid.uuid4().hex}"
    record = {
        "id": dream_id,
        "user_id": user_id,
        "title": data.get("title", ""),
        "dream_content": data.get("dream_content", ""),
        "simple_analysis": data.get("simple_analysis", ""),
        "deep_analysis": data.get("deep_analysis", ""),
        "category": data.get("category", "普通夢境"),
        "tags": data.get("tags", []),
        "created_at": datetime.utcnow()
    }
    dream_collection.insert_one(record)
    return jsonify({"success": True, "dream": record}), 201

# GET /dream-records 取得該用戶全部夢境
@app.route('/dream-records', methods=['GET'])
def fetch_all_dream():
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"success": False, "message": "未提供登入憑證"}), 401
    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        user_id = payload["userId"]
    except jwt.InvalidTokenError:
        return jsonify({"success": False, "message": "憑證無效或已過期"}), 401

    records = list(dream_collection.find({"user_id": user_id}).sort("created_at", -1))
    for item in records:
        item.pop("_id", None)
    return jsonify({"success": True, "records": records})

# DELETE /dream-record/<dream_id> 刪除夢境
@app.route('/dream-record/<dream_id>', methods=['DELETE'])
def delete_dream(dream_id):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"success": False, "message": "未提供登入憑證"}), 401
    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        user_id = payload["userId"]
    except jwt.InvalidTokenError:
        return jsonify({"success": False, "message": "憑證無效或已過期"}), 401

    result = dream_collection.delete_one({"id": dream_id, "user_id": user_id})
    if result.deleted_count == 0:
        return jsonify({"success": False, "message": "找不到夢境記錄或者無權限刪除"}), 404
    return jsonify({"success": True, "message": "夢境記錄已刪除"}), 200

# PUT /dream-record/<dream_id>/tags 更新夢境標籤
@app.route('/dream-record/<dream_id>/tags', methods=['PUT'])
def edit_dream_tags(dream_id):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"success": False, "message": "未提供登入憑證"}), 401
    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=["HS256"])
        user_id = payload["userId"]
    except jwt.InvalidTokenError:
        return jsonify({"success": False, "message": "憑證無效或已過期"}), 401

    req_data = request.get_json()
    tags_arr = req_data.get("tags", [])
    if not isinstance(tags_arr, list):
        return jsonify({"success": False, "message": "標籤格式錯誤，必須為陣列"}),400

    update_result = dream_collection.update_one(
        {"id": dream_id, "user_id": user_id},
        {"$set": {"tags": tags_arr}}
    )
    if update_result.matched_count ==0:
        return jsonify({"success":False, "message":"找不到夢境記錄或者無權限修改"}),404
    return jsonify({"success":True, "message":"標籤更新成功"}),200


# ====================== 會員 AUTH 全套接口（SMTP郵件版本） ======================
import hashlib
def hash_password(raw_pw):
    return hashlib.sha256(raw_pw.encode("utf-8")).hexdigest()

# SMTP發送郵件函數
def send_email(to_email, subject, body):
    if not EMAIL_SENDER or not EMAIL_PASS:
        print("缺少SMTP郵箱設定")
        return False
    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = EMAIL_SENDER
        msg["To"] = to_email
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
            server.login(EMAIL_SENDER, EMAIL_PASS)
            server.send_message(msg)
        return True
    except Exception as e:
        print("SMTP發信錯誤：", str(e))
        return False

# 1. POST /auth/send-code 發送註冊驗證碼
@app.route("/auth/send-code", methods=["POST"])
def send_register_code():
    data = request.get_json()
    email = data.get("email", "").strip().lower()
    if not email:
        return jsonify({"success":False, "message":"請輸入電郵"}),400
    code = ''.join(random.choices("0123456789", k=6))
    expire_at = datetime.utcnow() + timedelta(minutes=15)
    verify_collection.update_one({"email":email}, {"$set":{"code":code,"expire_at":expire_at}}, upsert=True)
    email_body = f"""Dream of Wisdom 夢境網站 註冊驗證碼
你的驗證碼：{code}
有效期15分鐘，請不要分享給其他人。"""
    ok = send_email(email, "DreamofWisdom 帳戶驗證碼", email_body)
    if not ok:
        return jsonify({"success":False, "message":"發送郵件失敗，請稍後重試"}),500
    return jsonify({"success":True, "message":"驗證碼已發送至電郵"}),200

# 2. POST /auth/register 提交驗證碼+密碼，開通帳號
@app.route("/auth/register", methods=["POST"])
def register_account():
    data = request.get_json()
    email = data.get("email","").strip().lower()
    code = data.get("code","").strip()
    password = data.get("password","")
    if not email or not code or not password:
        return jsonify({"success":False,"message":"缺少欄位"}),400
    if len(password) <6:
        return jsonify({"success":False,"message":"密碼最少6位，可使用英文字、數字、符號"}),400
    v_record = verify_collection.find_one({"email":email})
    if not v_record or v_record["code"] != code or v_record["expire_at"] < datetime.utcnow():
        return jsonify({"success":False,"message":"驗證碼錯誤或已過期"}),400
    exist_user = user_collection.find_one({"email":email})
    if exist_user:
        return jsonify({"success":False,"message":"此電郵已經註冊"}),400
    user_id = f"user_{uuid.uuid4().hex}"
    new_user = {
        "user_id": user_id,
        "email": email,
        "password_hash": hash_password(password),
        "star_coins":6,
        "adWatchCount":0,
        "created_at": datetime.utcnow()
    }
    user_collection.insert_one(new_user)
    verify_collection.delete_one({"email":email})
    token = jwt.encode({"userId":user_id, "exp":datetime.utcnow()+timedelta(days=7)}, JWT_SECRET_KEY, algorithm="HS256")
    return jsonify({"success":True, "token":token, "user":{"user_id":user_id,"email":email,"star_coins":6, "adWatchCount":0}}),201

#3. POST /auth/login 電郵密碼登入
@app.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email","").strip().lower()
    password = data.get("password","")
    if not email or not password:
        return jsonify({"success":False,"message":"請輸入電郵同密碼"}),400
    user = user_collection.find_one({"email":email})
    if not user or user["password_hash"] != hash_password(password):
        return jsonify({"success":False,"message":"電郵或密碼錯誤"}),401
    token = jwt.encode({"userId":user["user_id"], "exp":datetime.utcnow()+timedelta(days=7)}, JWT_SECRET_KEY, algorithm="HS256")
    return jsonify({
        "success":True,
        "token":token,
        "user":{
            "user_id":user["user_id"],
            "email":user["email"],
            "star_coins":user["star_coins"],
            "adWatchCount": user.get("adWatchCount",0)
        }
    })

#4. POST /auth/forgot-code 忘記密碼：發送重設密碼驗證碼
@app.route("/auth/forgot-code", methods=["POST"])
def send_forgot_code():
    data = request.get_json()
    email = data.get("email","").strip().lower()
    if not email:
        return jsonify({"success":False,"message":"請輸入電郵"}),400
    user = user_collection.find_one({"email":email})
    if not user:
        return jsonify({"success":False,"message":"找不到該電郵帳戶"}),404
    code = ''.join(random.choices("0123456789", k=6))
    expire_at = datetime.utcnow() + timedelta(minutes=15)
    verify_collection.update_one({"email":email}, {"$set":{"code":code,"expire_at":expire_at}}, upsert=True)
    email_body = f"""Dream of Wisdom 重設密碼驗證碼
你的重設密碼驗證碼：{code}
有效期15分鐘，如非本人操作可忽略此郵件。"""
    ok = send_email(email, "DreamofWisdom 重設密碼驗證碼", email_body)
    if not ok:
        return jsonify({"success":False, "message":"發送郵件失敗"}),500
    return jsonify({"success":True,"message":"驗證碼已發送"}),200

#5. POST /auth/reset-password 驗證碼 + 新密碼，重設密碼
@app.route("/auth/reset-password", methods=["POST"])
def reset_password():
    data = request.get_json()
    email = data.get("email","").strip().lower()
    code = data.get("code","").strip()
    new_password = data.get("password","")
    if len(new_password)<6:
        return jsonify({"success":False,"message":"密碼最少6位，可使用英文字、數字、符號"}),400
    v_record = verify_collection.find_one({"email":email})
    if not v_record or v_record["code"] != code or v_record["expire_at"] < datetime.utcnow():
        return jsonify({"success":False,"message":"驗證碼錯誤或過期"}),400
    user = user_collection.find_one({"email":email})
    if not user:
        return jsonify({"success":False,"message":"帳戶不存在"}),404
    user_collection.update_one({"email":email}, {"$set":{"password_hash": hash_password(new_password)}})
    verify_collection.delete_one({"email":email})
    return jsonify({"success":True,"message":"密碼重設成功，可登入"}),200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
