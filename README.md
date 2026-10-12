# DreamofWisdom - dream-api（Flask後端）
Render 服務：dream-api
網址：https://dream-api-gfrb.onrender.com

## 功能
- DeepSeek AI 解夢分析
- POST `/save-dream`：儲存會員夢境紀錄入 MongoDB `dream_records`
- GET `/dream-history`：根據 userId 讀取該用戶所有夢境紀錄

## 技術
Python + Flask + pymongo
主要檔案：
- app.py：主程式，所有API接口
- requirements.txt：Python依賴套件

## 環境變數（Render設定）
- MONGODB_URI：MongoDB Atlas連接字串
- DEEPSEEK_API_KEY：DeepSeek AI金鑰

## CORS
允許來源：dreamofwisdom.com, dreamofwisdom.onrender.com

> 備註：本服務**唔處理會員註冊登入**，會員認證由 DreamofWisdom-Auth 負責。
> 接收前端傳入 userId，綁定夢境紀錄。
