from flask import Flask, request, jsonify, send_from_directory
from openai import OpenAI
import os, json

from docx import Document
from PyPDF2 import PdfReader

app = Flask(__name__, static_folder="static")

# 初始化 OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/<path:path>")
def static_files(path):
    return send_from_directory("static", path)

# 翻譯文字
@app.route("/translate", methods=["POST"])
def translate_text():
    data = request.get_json()
    text = data.get("text", "").strip()
    target_lang = data.get("target_lang", "繁體中文").strip()

    if not text:
        return jsonify({"error": "缺少翻譯文字"}), 400

    try:
        prompt = f"請將以下文字翻譯成 {target_lang}：\n{text}"
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "你是一個專業翻譯助手。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
        result = response.choices[0].message.content
        return jsonify({"result": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 翻譯文件
@app.route("/translate_file", methods=["POST"])
def translate_file():
    if "file" not in request.files:
        return jsonify({"error": "未上傳檔案"}), 400

    target_lang = request.form.get("target_lang", "繁體中文")
    file = request.files["file"]
    filename = file.filename.lower()

    try:
        # 讀取檔案內容
        if filename.endswith(".txt"):
            content = file.read().decode("utf-8")
        elif filename.endswith(".docx"):
            doc = Document(file)
            content = "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
        elif filename.endswith(".pdf"):
            reader = PdfReader(file)
            content = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
        else:
            return jsonify({"error": "不支援的檔案格式"}), 400

        if not content.strip():
            return jsonify({"error": "檔案內容為空"}), 400

        # 丟給 GPT 翻譯
        prompt = f"請將以下文件完整翻譯成 {target_lang}：\n{content}"
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "你是一個專業翻譯助手，請翻譯完整文件"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
        result = response.choices[0].message.content
        return jsonify({"result": result})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
