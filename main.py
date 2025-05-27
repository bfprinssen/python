from flask import Flask, request, render_template_string
from bs4 import BeautifulSoup
import requests
import time

app = Flask(__name__)

# HTML-template als string (geïntegreerd)
html_form = '''
<!DOCTYPE html>
<html lang="nl">
<head>
  <meta charset="UTF-8">
  <title>Golfscore Invoeren</title>
  <style>
    body { font-family: Arial, sans-serif; max-width: 600px; margin: 40px auto; }
    label { display: block; margin-top: 15px; font-weight: bold; }
    input, select, button {
      width: 100%; padding: 8px; margin-top: 5px; border-radius: 6px; border: 1px solid #ccc;
    }
    button {
      background-color: #4CAF50; color: white; font-weight: bold; cursor: pointer;
    }
    button:hover { background-color: #45a049; }
    .result { margin-top: 20px; font-size: 18px; font-weight: bold; }
  </style>
</head>
<body>
  <h2>Voer je golfscore in</h2>
  <form method="post">
    <label for="url">Golfbaan-URL:</label>
    <input type="url" id="url" name="url" required placeholder="https://...">
    <label for="hole">Hole (1-18):</label>
    <select id="hole" name="hole">
      {% for i in range(1, 19) %}
        <option value="{{ i }}">{{ i }}</option>
      {% endfor %}
    </select>
    <label for="score">Aantal slagen:</label>
    <input type="number" id="score" name="score" min="1" required>
    <button type="submit">Verstuur</button>
  </form>
  {% if result %}
    <p class="result">Je score op hole {{ hole }} is: <strong>{{ result }}</strong></p>
  {% endif %}
</body>
</html>
'''

# Functie om pars te scrapen van een golfbaan
def scrape_pars(url, debug=False):
    debug_msgs = []
    pars = {}
    try:
        response = requests.get(url)
        debug_msgs.append(f"Status code: {response.status_code}")
        if response.status_code != 200:
            debug_msgs.append("Kon de pagina niet ophalen.")
            return None if not debug else debug_msgs
        soup = BeautifulSoup(response.text, "html.parser")
        # Zoek naar tabellen
        tables = soup.find_all("table")
        debug_msgs.append(f"Aantal tabellen gevonden: {len(tables)}")
        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                cells = row.find_all(["td", "th"])
                texts = [cell.get_text(strip=True) for cell in cells]
                # Zoek naar een rij met per-hole par (meestal: eerste cell 'Par', daarna getallen)
                if texts and (texts[0].lower() == "par" or "par" in texts[0].lower()):
                    par_values = [int(t) for t in texts[1:] if t.isdigit()]
                    debug_msgs.append(f"Par-rij per hole gevonden: {texts}")
                    if par_values:
                        hole_numbers = list(range(1, len(par_values)+1))
                        debug_msgs.append(f"par_values: {par_values}")
                        pars = dict(zip(hole_numbers, par_values))
                        return pars if not debug else (pars, debug_msgs)
                # Alternatief: als alleen totaal par gevonden wordt
                elif any(t.lower().startswith("par ") and t[4:].isdigit() for t in texts):
                    debug_msgs.append(f"Alleen totaalscore gevonden: {texts}")
                    return None if not debug else debug_msgs
        debug_msgs.append("Geen par-rij per hole gevonden in tabellen.")
        return None if not debug else debug_msgs
    except Exception as e:
        debug_msgs.append(f"Fout: {e}")
        return None if not debug else debug_msgs


# Interpretatie van score vs par
def interpret_score(par, score):
    verschil = score - par
    if verschil == 0:
        return "Par"
    elif verschil == -1:
        return "Birdie"
    elif verschil == -2:
        return "Eagle"
    elif verschil == -3:
        return "Albatross"
    elif verschil == 1:
        return "Bogey"
    elif verschil == 2:
        return "Double Bogey"
    elif verschil > 2:
        return f"{verschil}-over par"
    else:
        return f"{abs(verschil)}-under par"

@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    hole = None
    debug_msgs = None
    if request.method == "POST":
        url = request.form["url"]
        hole = int(request.form["hole"])
        score = int(request.form["score"])
        scrape_result = scrape_pars(url, debug=True)
        if isinstance(scrape_result, tuple):
            pars, debug_msgs = scrape_result
        else:
            pars = scrape_result
        if not pars or hole not in pars:
            result = "Fout bij het ophalen van de par voor deze hole."
        else:
            par = pars[hole]
            result = interpret_score(par, score)

    return render_template_string(html_form + '{% if debug_msgs %}<pre style="margin-top:30px; background:#eee; padding:10px;">{{ debug_msgs|join("\n") }}</pre>{% endif %}', result=result, hole=hole, debug_msgs=debug_msgs)

if __name__ == "__main__":
    app.run(debug=True)
