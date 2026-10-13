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
from bson import ObjectId

app = Flask(__name__)

CORS(app,
     origins=[
         "https://dreamofwisdom.com",
         "https://www.dreamofwisdom.com"
     ],
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "OPTIONS"])

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
API_URL = "https://api.deepseek.com/v1/chat/completions"
MONGODB_URI = os.environ.get("MONGODB_URI")
JWT_SECRET = os.environ.get("JWT_SECRET")

client = MongoClient(MONGODB_URI)
db = client["dreamofwisdom"]
users_col = db["users"]
records_col = db["dream_records"]

def generate_token(user_id):
    payload = {"uid": str(user_id), "exp": datetime.utcnow().timestamp() + 86400*7}
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def get_uid_from_token():
    auth = request.headers.get("Authorization","")
    if not auth.startswith("Bearer "):
        return None
    token = auth.replace("Bearer ","")
    try:
        dec = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return dec["uid"]
    except Exception:
        return None

@app.route("/")
def index():
    return "DreamWisdom API Ready", 200

# 初步解夢，免登入免星星
@app.route("/analyze", methods=["POST"])
def analyze():
    data = request.get_json()
    prompt = data.get("dream","")
    if not prompt:
        return jsonify({"success":False, "message":"請輸入夢境"}),400
    payload = {
        "model":"deepseek-chat",
        "messages":[{"role":"user","content":f"你係專業解夢師，廣東話口吻解夢：{prompt}"}]
    }
    res = requests.post(API_URL, headers={"Authorization":f"Bearer {DEEPSEEK_API_KEY}"}, json=payload)
    return jsonify(res.json())

# 深度解夢：登入、檢查星星、扣1粒星星
@app.route("/deep-analyze", methods=["POST"])
def deep_analyze():
    uid = get_uid_from_token()
    if not uid:
        return jsonify({"success":False,"message":"請先登入會員"}),401
    user = users_col.find_one({"_id":ObjectId(uid)})
    if not user:
        return jsonify({"success":False,"message":"用戶不存在"}),404
    if user.get("stars",0) <= 0:
        return jsonify({"success":False,"message":"星星不足，請觀看廣告獲取星星"}),400

    # 扣星星
    users_col.update_one({"_id":ObjectId(uid)}, {"$inc":{"stars": -1}})

    data = request.get_json()
    prompt = data.get("dream","")
    payload = {
        "model":"deepseek-chat",
        "messages":[{"role":"user","content":f"深度心理學解夢，詳細分析：{prompt}"}]
    }
    res = requests.post(API_URL, headers={"Authorization":f"Bearer {DEEPSEEK_API_KEY}"}, json=payload)
    return jsonify(res.json())

# 註冊：電郵密碼直接註冊，無郵件驗證
@app.route("/auth/register", methods=["POST"])
def register():
    data = request.get_json()
    email = data.get("email","").strip()
    pwd = data.get("password","")
    if not email or not pwd:
        return jsonify({"success":False,"message":"電郵同密碼唔可以留空"}),400
    exist = users_col.find_one({"email":email})
    if exist:
        return jsonify({"success":False,"message":"電郵已經註冊"}),400
    hash_pwd = bcrypt.hashpw(pwd.encode(), bcrypt.gensalt())
    new_user = {
        "email": email,
        "password": hash_pwd,
        "stars": 0,
        "adWatchCount": 0,
        "created_at": datetime.utcnow()
    }
    uid = users_col.insert_one(new_user).inserted_id
    token = generate_token(uid)
    return jsonify({
        "success": True,
        "token": token,
        "user": {"email": email, "stars": 0}
    })

# 登入
@app.route("/auth/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email","").strip()
    pwd = data.get("password","")
    u = users_col.find_one({"email":email})
    if not u or not bcrypt.checkpw(pwd.encode(), u["password"]):
        return jsonify({"success":False,"message":"電郵或密碼錯誤"}),401
    token = generate_token(u["_id"])
    return jsonify({
        "success": True,
        "token": token,
        "user": {"email": u["email"], "stars": u.get("stars",0), "adWatchCount": u.get("adWatchCount",0)}
    })

# 儲存夢境紀錄
@app.route("/dream-record", methods=["POST"])
def save_record():
    uid = get_uid_from_token()
    if not uid:
        return jsonify({"success":False,"message":"請先登入"}),401
    data = request.get_json()
    data["uid"] = uid
    data["created_at"] = datetime.utcnow()
    ret = records_col.insert_one(data)
    return jsonify({"success":True, "record_id":str(ret.inserted_id)})

# 讀取夢境歷史
@app.route("/dream-records", methods=["GET"])
def list_records():
    uid = get_uid_from_token()
    if not uid:
        return jsonify({"success":False,"message":"請先登入"}),401
    lst = list(records_col.find({"uid":uid}).sort("created_at",-1))
    for x in lst:
        x["_id"] = str(x["_id"])
    return jsonify({"success":True, "records":lst})

# 睇廣告：累計3次 → +3星星（唯一星星渠道）
@app.route("/watch-ad", methods=["POST"])
def watch_ad():
    uid = get_uid_from_token()
    if not uid:
        return jsonify({"success":False,"message":"請先登入"}),401
    user = users_col.find_one({"_id":ObjectId(uid)})
    cnt = user.get("adWatchCount",0)+1
    if cnt >=3:
        users_col.update_one({"_id":ObjectId(uid)}, {"$set":{"adWatchCount":0}, "$inc":{"stars":3}})
        return jsonify({"success":True,"message":"累計3個廣告，已獲得3粒星星！"})
    else:
        users_col.update_one({"_id":ObjectId(uid)}, {"$set":{"adWatchCount":cnt}})
        return jsonify({"success":True,"message":f"已觀看廣告 {cnt}/3"})

# 取得個人資料、星星、廣告次數
@app.route("/me", methods=["GET"])
def me():
    uid = get_uid_from_token()
    if not uid:
        return jsonify({"success":False,"message":"請先登入"}),401
    u = users_col.find_one({"_id":ObjectId(uid)})
    if not u:
        return jsonify({"success":False,"message":"用戶不存在"}),404
    return jsonify({
        "success":True,
        "user":{
            "email":u["email"],
            "stars":u.get("stars",0),
            "adWatchCount":u.get("adWatchCount",0)
        }
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",5000)))
