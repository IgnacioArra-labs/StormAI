from flask import Flask, render_template, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from flask_caching import Cache
import logging

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Configuración de caché
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

# Configuración de logging
logging.basicConfig(filename='app.log', level=logging.INFO)

def fix_encoding_issues(text):
    try:
        return text.encode('latin1').decode('utf-8')
    except UnicodeDecodeError:
        return text

def convert_to_float(value):
    try:
        return float(value.replace('°C', '').replace('%', '').strip())
    except ValueError:
        return None

@cache.cached(timeout=300, key_prefix='weather_data')
def obtener_datos_en_tiempo_real():
    try:
        options = Options()
        options.add_argument("--headless")
        driver = webdriver.Chrome(options=options)
        driver.get("https://contingencias.mendoza.gov.ar/instantaneas/")

        table = driver.find_element(By.XPATH, '//table[@border="1"]')
        rows = table.find_elements(By.TAG_NAME, "tr")
        data = {}

        for row in rows[1:]:
            cols = row.find_elements(By.TAG_NAME, "td")
            cols = [fix_encoding_issues(col.text.strip()) for col in cols]
            if len(cols) == 5:
                fecha_hora = cols[1].split(' ')
                data[cols[0]] = {
                    "Nombre": cols[0],
                    "Fecha": fecha_hora[0],
                    "Hora": fecha_hora[1],
                    "Temperatura": convert_to_float(cols[2]),
                    "Humedad": convert_to_float(cols[3]),
                    "P. Rocio": convert_to_float(cols[4])
                }
        logging.info('Datos raspados exitosamente.')
        return data
    except Exception as e:
        logging.error(f"Error durante el scraping: {e}")
        return {}
    finally:
        driver.quit()

@app.route('/api/datos/<string:ubicacion>', methods=['GET'])
def api_datos_por_ubicacion(ubicacion):
    datos = obtener_datos_en_tiempo_real().get(ubicacion)
    if datos:
        return jsonify(datos)
    return jsonify({"error": "Ubicación no encontrada"}), 404

@app.route('/api/datos', methods=['GET'])
def api_todos_los_datos():
    datos = obtener_datos_en_tiempo_real()
    return jsonify(datos)

@app.route('/')
def index():
    data = obtener_datos_en_tiempo_real()
    return render_template('index.html', data=data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
