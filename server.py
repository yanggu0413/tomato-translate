from flask import Flask, request, jsonify, send_from_directory, Response
from openai import OpenAI
from werkzeug.utils import secure_filename
import os
import json
import tempfile
from docx import Document
from PyPDF2 import PdfReader

# 初始化
app = Flask(__name__, static_folder="static")
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# 靜態頁面
@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/<path:path>")
def static_files(path):
    return send_from_directory("static", path)

# 翻譯 API
@app.route("/translate", methods=["POST"])
def translate():
    try:
        data = request.get_json()
        text = (data.get("text") or "").strip()
        target_lang = (data.get("target_lang") or "繁體中文").strip()

        if not text:
            return jsonify({"error": "缺少要翻譯的文字"}), 400

        prompt = (
            f"請自動偵測以下文字的語言，並翻譯成 {target_lang}：\n"
            f"---\n{text}\n---\n"
            f"請用 JSON 格式回覆：{{\"detected_lang\": \"來源語言\", \"translation\": \"翻譯結果\"}}"
        )

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "你是一個專業翻譯助手。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
        content = response.choices[0].message.content.strip()

        try:
            result_json = json.loads(content)
            return jsonify({
                "result": result_json.get("translation", "翻譯失敗"),
                "detected": result_json.get("detected_lang", "未知")
            })
        except:
            return jsonify({"result": content, "detected": "未知"})

    except Exception as e:
        print("後端錯誤：", e)
        return jsonify({"error": str(e)}), 500

# 文件翻譯 API
@app.route("/file-translate", methods=["POST"])
def file_translate():
    try:
        if "file" not in request.files:
            return jsonify({"error": "未收到檔案"}), 400
        f = request.files["file"]
        target_lang = request.form.get("target_lang", "繁體中文")

        filename = secure_filename(f.filename)
        ext = filename.split(".")[-1].lower()

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, filename)
            f.save(path)

            text = ""
            if ext == "txt":
                text = open(path, "r", encoding="utf-8", errors="ignore").read()
            elif ext == "docx":
                doc = Document(path)
                text = "\n".join([p.text for p in doc.paragraphs])
            elif ext == "pdf":
                reader = PdfReader(path)
                text = "\n".join([p.extract_text() for p in reader.pages])
            else:
                return jsonify({"error": "不支援的格式"}), 400

        prompt = (
            f"請翻譯以下文件內容成 {target_lang}：\n"
            f"---\n{text}\n---"
        )
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": "你是一個專業翻譯助手"},
                      {"role": "user", "content": prompt}],
            temperature=0.2
        )
        result = response.choices[0].message.content.strip()
        return jsonify({"result": result})

    except Exception as e:
        print("文件翻譯錯誤：", e)
        return jsonify({"error": str(e)}), 500

# 語音 TTS
@app.route("/tts", methods=["POST"])
def tts():
    try:
        data = request.get_json()
        text = (data.get("text") or "").strip()
        voice = data.get("voice", "alloy")
        rate = float(data.get("rate", 1.0))
        lang_code = data.get("lang_code", "zh-TW")

        if not text:
            return jsonify({"error": "沒有文字"}), 400

        prompt = f"Language: {lang_code}. Please speak at {rate:.2f}x speed. Text: {text}"
        audio = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice=voice,
            input=prompt,
            format="mp3"
        )
        mp3_bytes = audio.read()
        return Response(mp3_bytes, mimetype="audio/mpeg",
                        headers={"Content-Disposition": "attachment; filename=speech.mp3"})
    except Exception as e:
        print("TTS 錯誤：", e)
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
