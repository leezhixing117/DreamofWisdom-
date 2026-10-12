import sys
sys.stdout.reconfigure(encoding='utf-8')
import os
import jwt
import uuid
import random
from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from pymongo import MongoClient
from datetime import datetime, timedelta

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
JWT_SECRET = os.environ.get("JWT_SECRET")
# 郵件發送用（使用mailgun / 可替換其他smtp，你後續填環境變數）
MAIL_FROM = os.environ.get("MAIL_FROM")
MAILGUN_API_KEY = os.environ.get("MAILGUN_API_KEY")
MAILGUN_DOMAIN = os.environ.get("MAILGUN_DOMAIN")

# 連接MongoDB
client = MongoClient(MONGODB_URI)
db = client["dreamofwisdom_db"]
dream_collection = db["dream_records"]
user_collection = db["members"]
verify_collection = db["email_verify_codes"]

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

# 【舊接口】讀取某用戶所有夢境記錄（用於生成past_records）
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


# ============ 全新 JWT 認證夢境API (對接dreamApi.js) ============
# POST /api/dream-record 新增儲存夢境紀錄
@app.route('/api/dream-record', methods=['POST'])
def save_dream_record():
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"success": False, "message": "未提供登入憑證"}), 401
    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
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
        "deep_result": data.get("deep_result", ""),
        "category": data.get("category", "普通夢境"),
        "tags": data.get("tags", []),
        "created_at": datetime.utcnow()
    }
    dream_collection.insert_one(record)
    return jsonify({"success": True, "dream": record}), 201


# GET /api/dream-records 讀取登入用戶全部夢境
@app.route('/api/dream-records', methods=['GET'])
def get_all_dream_records():
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"success": False, "message": "未提供登入憑證"}), 401
    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user_id = payload["userId"]
    except jwt.InvalidTokenError:
        return jsonify({"success": False, "message": "憑證無效或已過期"}), 401

    records = list(dream_collection.find({"user_id": user_id}).sort("created_at", -1))
    res_list = []
    for item in records:
        res_list.append({
            "id": item["id"],
            "title": item.get("title", ""),
            "dream_content": item["dream_content"],
            "simple_analysis": item.get("simple_analysis", ""),
            "deep_result": item.get("deep_result", ""),
            "category": item.get("category", "普通夢境"),
            "tags": item.get("tags", []),
            "created_at": item["created_at"].isoformat()
        })
    return jsonify({"success": True, "records": res_list})


# DELETE /api/dream-record/<dream_id> 刪除夢境紀錄
@app.route('/api/dream-record/<dream_id>', methods=['DELETE'])
def delete_dream_record(dream_id):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"success": False, "message": "未提供登入憑證"}), 401
    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user_id = payload["userId"]
    except jwt.InvalidTokenError:
        return jsonify({"success": False, "message": "憑證無效或已過期"}), 401

    try:
        result = dream_collection.delete_one({
            "id": dream_id,
            "user_id": user_id
        })
        if result.deleted_count == 0:
            return jsonify({"success": False, "message": "找不到夢境記錄或者無權限刪除"}), 404
        return jsonify({"success": True, "message": "夢境記錄已刪除"}), 200
    except Exception as e:
        print("刪除夢境錯誤：", str(e))
        return jsonify({"success": False, "message": "伺服器刪除失敗"}), 500


# PUT /api/dream-record/<dream_id>/tags 更新夢境標籤tags
@app.route('/api/dream-record/<dream_id>/tags', methods=['PUT'])
def update_dream_tags(dream_id):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return jsonify({"success": False, "message": "未提供登入憑證"}), 401
    token = auth_header.split(" ")[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        user_id = payload["userId"]
    except jwt.InvalidTokenError:
        return jsonify({"success": False, "message": "憑證無效或已過期"}), 401

    data = request.get_json()
    new_tags = data.get("tags", [])
    if not isinstance(new_tags, list):
        return jsonify({"success": False, "message": "標籤格式錯誤，必須為陣列"}), 400

    try:
        result = dream_collection.update_one(
            {
                "id": dream_id,
                "user_id": user_id
            },
            {
                "$set": {
                    "tags": new_tags
                }
            }
        )
        if result.matched_count == 0:
            return jsonify({"success": False, "message": "找不到夢境記錄或者無權限修改"}), 404
        return jsonify({"success": True, "message": "標籤更新成功"}), 200
    except Exception as e:
        print("更新標籤錯誤：", str(e))
        return jsonify({"success": False, "message": "更新標籤失敗"}), 500


# ====================== 會員 AUTH 全套接口 ======================
import hashlib
def hash_password(raw_pw):
    return hashlib.sha256(raw_pw.encode("utf-8")).hexdigest()

# 寄驗證碼函數（Mailgun）
def send_email(to_email, subject, body):
    if not MAILGUN_API_KEY or not MAILGUN_DOMAIN:
        return False
    url = f"https://api.mailgun.net/v3/{MAILGUN_DOMAIN}/messages"
    auth_data = ("api", MAILGUN_API_KEY)
    data = {
        "from": MAIL_FROM,
        "to": to_email,
        "subject": subject,
        "text": body
    }
    r = requests.post(url, auth=auth_data, data=data)
    return r.status_code == 200

# 1. POST /api/auth/send-code 發送註冊驗證碼
@app.route("/api/auth/send-code", methods=["POST"])
def send_register_code():
    data = request.get_json()
    email = data.get("email", "").strip().lower()
    if not email:
        return jsonify({"success":False, "message":"請輸入電郵"}),400
    # 6位數驗證碼
    code = ''.join(random.choices("0123456789", k=6))
    expire_at = datetime.utcnow() + timedelta(minutes=15)
    # 覆蓋舊同email驗證紀錄
    verify_collection.update_one({"email":email}, {"$set":{"code":code,"expire_at":expire_at}}, upsert=True)
    email_body = f"""Dream of Wisdom 夢境網站 註冊驗證碼
你的驗證碼：{code}
有效期15分鐘，請不要分享給其他人。"""
    ok = send_email(email, "DreamofWisdom 帳戶驗證碼", email_body)
    if not ok:
        return jsonify({"success":False, "message":"發送郵件失敗，請稍後重試"}),500
    return jsonify({"success":True, "message":"驗證碼已發送至電郵"}),200

# 2. POST /api/auth/register 提交驗證碼+密碼，開通帳號（新會員送6星星幣）
@app.route("/api/auth/register", methods=["POST"])
def register_account():
    data = request.get_json()
    email = data.get("email","").strip().lower()
    code = data.get("code","").strip()
    password = data.get("password","")
    if not email or not code or not password:
        return jsonify({"success":False,"message":"缺少欄位"}),400
    # 密碼規則：最少6位，英數+符號
    if len(password) <6:
        return jsonify({"success":False,"message":"密碼最少6位"}),400
    # 查驗證碼
    v_record = verify_collection.find_one({"email":email})
    if not v_record or v_record["code"] != code or v_record["expire_at"] < datetime.utcnow():
        return jsonify({"success":False,"message":"驗證碼錯誤或已過期"}),400
    # 檢查帳號是否已註冊
    exist_user = user_collection.find_one({"email":email})
    if exist_user:
        return jsonify({"success":False,"message":"此電郵已經註冊"}),400
    user_id = f"user_{uuid.uuid4().hex}"
    new_user = {
        "user_id": user_id,
        "email": email,
        "password_hash": hash_password(password),
        "star_coins":6,
        "created_at": datetime.utcnow()
    }
    user_collection.insert_one(new_user)
    # 清除已使用驗證碼
    verify_collection.delete_one({"email":email})
    # 簽發JWT token，有效期7天
    token = jwt.encode({"userId":user_id, "exp":datetime.utcnow()+timedelta(days=7)}, JWT_SECRET, algorithm="HS256")
    return jsonify({"success":True, "token":token, "user":{"user_id":user_id,"email":email,"star_coins":6}}),201

#3. POST /api/auth/login 電郵密碼登入
@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email","").strip().lower()
    password = data.get("password","")
    if not email or not password:
        return jsonify({"success":False,"message":"請輸入電郵同密碼"}),400
    user = user_collection.find_one({"email":email})
    if not user or user["password_hash"] != hash_password(password):
        return jsonify({"success":False,"message":"電郵或密碼錯誤"}),401
    token = jwt.encode({"userId":user["user_id"], "exp":datetime.utcnow()+timedelta(days=7)}, JWT_SECRET, algorithm="HS256")
    return jsonify({
        "success":True,
        "token":token,
        "user":{
            "user_id":user["user_id"],
            "email":user["email"],
            "star_coins":user["star_coins"]
        }
    })

#4. POST /api/auth/forgot-code 忘記密碼：發送重設密碼驗證碼
@app.route("/api/auth/forgot-code", methods=["POST"])
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

#5. POST /api/auth/reset-password 驗證碼 + 新密碼，重設密碼
@app.route("/api/auth/reset-password", methods=["POST"])
def reset_password():
    data = request.get_json()
    email = data.get("email","").strip().lower()
    code = data.get("code","").strip()
    new_password = data.get("password","")
    if len(new_password)<6:
        return jsonify({"success":False,"message":"密碼最少6位"}),400
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
