from flask import Flask, request, jsonify, send_from_directory
from openai import OpenAI
import os, json

# 初始化 Flask
app = Flask(__name__, static_folder="static")

# 初始化 OpenAI Client，從環境變數讀取 API Key
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 首頁 (靜態檔案)
@app.route("/")
def index():
    return send_from_directory("static", "index.html")

# 靜態檔案 (copy.png 等)
@app.route("/<path:path>")
def static_files(path):
    return send_from_directory("static", path)

# 翻譯 API
@app.route("/translate", methods=["POST"])
def translate():
    data = request.get_json()
    text = data.get("text", "").strip()
    target_lang = data.get("target_lang", "繁體中文").strip()

    if not text:
        return jsonify({"error": "缺少翻譯文字"}), 400

    try:
        prompt = (
            f"請自動偵測以下文字的語言，並翻譯成 {target_lang}：\n"
            f"---\n{text}\n---\n"
            f"請用 JSON 格式回覆：{{\"detected_lang\": \"來源語言\", \"translation\": \"翻譯結果\"}}"
        )

        # 使用新版 OpenAI API 呼叫 GPT
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Render 免費版可用此模型
            messages=[
                {"role": "system", "content": "你是一個專業翻譯助手。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )

        content = response.choices[0].message.content

        try:
            # 嘗試解析 JSON 格式回應
            result_json = json.loads(content)
            return jsonify({
                "result": result_json.get("translation", "翻譯失敗"),
                "detected": result_json.get("detected_lang", "未知")
            })
        except json.JSONDecodeError:
            # 如果模型回的不是 JSON 格式，就直接顯示
            return jsonify({"result": content, "detected": "未知"})

    except Exception as e:
        print(f"❌ 翻譯錯誤：{e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # Render 會自動設定 PORT 環境變數
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
