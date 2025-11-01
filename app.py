import os
import pytesseract

# 🔧 Força o caminho absoluto do Tesseract no ambiente Linux (Render)
pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"

# Apenas para debug — opcional
if not os.path.exists(pytesseract.pytesseract.tesseract_cmd):
    print("⚠️ Caminho do Tesseract não encontrado:", pytesseract.pytesseract.tesseract_cmd)
else:
    print("✅ Tesseract encontrado em:", pytesseract.pytesseract.tesseract_cmd)

import os
import re
import io
from collections import Counter
from flask import Flask, render_template, request, redirect, url_for, send_file, flash
from werkzeug.utils import secure_filename
from pdf2image import convert_from_bytes
from PIL import Image
import pytesseract
import csv
from datetime import datetime

UPLOAD_EXTENSIONS = {'.pdf', '.png', '.jpg', '.jpeg'}
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50 MB

pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'


app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH
app.secret_key = os.environ.get("FLASK_SECRET", "trocar_para_valor_secreto")

# If Tesseract is not in PATH on the host, uncomment and set the correct path:
# pytesseract.pytesseract.tesseract_cmd = r"/usr/bin/tesseract"

def extrair_texto_de_imagem(pil_img):
    img = pil_img.convert('RGB')
    # opcional: aumentar resolução para melhora do OCR
    if img.width < 1200:
        new_w = int(img.width * 2)
        new_h = int(img.height * 2)
        img = img.resize((new_w, new_h), Image.LANCZOS)
    texto = pytesseract.image_to_string(img, lang='por+eng')
    return texto

def arquivo_para_texto(file_bytes, ext):
    texto_total = ""
    if ext == '.pdf':
        imagens = convert_from_bytes(file_bytes, dpi=300)
        for im in imagens:
            texto_total += "\n" + extrair_texto_de_imagem(im)
    else:
        im = Image.open(io.BytesIO(file_bytes))
        texto_total = extrair_texto_de_imagem(im)
    return texto_total

def analisar_milhares(texto, filtro_minimo=25):
    milhares = re.findall(r"\\b\\d{4}\\b", texto)
    filtradas = [m for m in milhares if int(m) > filtro_minimo]
    centenas = [m[-3:] for m in filtradas]
    dezenas = [m[-2:] for m in filtradas]
    cont_milhar = Counter(filtradas)
    cont_centena = Counter(centenas)
    cont_dezena = Counter(dezenas)
    return cont_milhar.most_common(), cont_centena.most_common(), cont_dezena.most_common()

def gerar_csv_bytes(milhares, centenas, dezenas):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Categoria", "Número", "Repetições"])
    for num, qtd in milhares:
        writer.writerow(["milhar", num, qtd])
    for num, qtd in centenas:
        writer.writerow(["centena", num, qtd])
    for num, qtd in dezenas:
        writer.writerow(["dezena", num, qtd])
    bytes_io = io.BytesIO()
    bytes_io.write(output.getvalue().encode('utf-8'))
    bytes_io.seek(0)
    return bytes_io

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html', resultado=None)

@app.route('/analisar', methods=['POST'])
def analisar():
    if 'arquivo' not in request.files:
        flash("Nenhum arquivo enviado.")
        return redirect(url_for('index'))

    f = request.files['arquivo']
    filename = secure_filename(f.filename)
    if filename == '':
        flash("Nenhum arquivo selecionado.")
        return redirect(url_for('index'))

    ext = os.path.splitext(filename)[1].lower()
    if ext not in UPLOAD_EXTENSIONS:
        flash("Formato não suportado. Use PDF, JPG ou PNG.")
        return redirect(url_for('index'))

    file_bytes = f.read()
    try:
        texto = arquivo_para_texto(file_bytes, ext)
    except Exception as e:
        flash(f"Erro ao processar o arquivo: {e}")
        return redirect(url_for('index'))

    milhares, centenas, dezenas = analisar_milhares(texto)
    key = datetime.utcnow().strftime('%Y%m%d%H%M%S%f')
    app.config.setdefault('RESULTS', {})
    app.config['RESULTS'][key] = {
        'milhares': milhares,
        'centenas': centenas,
        'dezenas': dezenas
    }

    return render_template('index.html',
                           resultado={
                               'milhares': milhares,
                               'centenas': centenas,
                               'dezenas': dezenas,
                               'key': key,
                               'arquivo': filename
                           })

@app.route('/baixar/<key>', methods=['GET'])
def baixar(key):
    results = app.config.get('RESULTS', {}).get(key)
    if not results:
        flash("Resultado não encontrado (expirado?). Gere novamente.")
        return redirect(url_for('index'))
    csv_bytes = gerar_csv_bytes(results['milhares'], results['centenas'], results['dezenas'])
    return send_file(csv_bytes,
                     as_attachment=True,
                     download_name="analise_milhares.csv",
                     mimetype='text/csv')

if __name__ == '__main__':
    # Para deploy em Render/Gunicorn, use gunicorn app:app
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
