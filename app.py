import os
import re
import json
import requests
from flask import Flask, request, render_template, redirect, jsonify, flash

app = Flask(__name__, static_url_path='/static')
# Utiliser une clé fixe pour éviter de perdre la session (et les messages flash) au redémarrage
app.secret_key = "netflixos_secret_key_change_me"

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, 'config.json')

# Valeurs par défaut vides pour forcer la configuration
DEFAULT_CONFIG = {
    "QB_URL": "",
    "JACKETT_URL": "",
    "QB_USER": "",
    "QB_PASS": "",
    "TMDB_KEY": "",
    "OMDB_KEY": "",
    "JACKETT_API_KEY": ""
}

def load_config():
    """Charge la configuration depuis le fichier JSON ou retourne les défauts."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                loaded_config = json.load(f)
                # On fusionne pour s'assurer qu'on a toutes les clés, même si le fichier est partiel
                return {**DEFAULT_CONFIG, **loaded_config}
        except Exception as e:
            print(f"Erreur lors du chargement de la config: {e}")
            pass
    return DEFAULT_CONFIG.copy()

def save_config(new_config):
    """Sauvegarde la configuration dans le fichier JSON."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(new_config, f, indent=4)
    except Exception as e:
        print(f"Erreur lors de la sauvegarde de la config: {e}")

# Chargement initial de la configuration
CONFIG = load_config()

@app.before_request
def check_configuration():
    """Vérifie si la configuration est complète avant chaque requête."""
    # On recharge la config à chaque requête pour être sûr d'avoir les dernières modifications
    global CONFIG
    CONFIG = load_config()

    # Liste des endpoints (routes) autorisés même sans configuration
    allowed_endpoints = ['settings', 'update_settings', 'static']
    
    # Si c'est un fichier statique (CSS, JS, Images), on laisse passer
    if request.path.startswith('/static/'):
        return

    # Si on est déjà sur une page autorisée, on laisse passer
    if request.endpoint and request.endpoint in allowed_endpoints:
        return

    # Vérification : est-ce qu'il manque des valeurs OBLIGATOIRES ?
    # On ne vérifie que les clés présentes dans DEFAULT_CONFIG
    missing = [k for k in DEFAULT_CONFIG.keys() if not CONFIG.get(k) or str(CONFIG.get(k)).strip() == ""]
    
    if missing:
        flash(f"Configuration incomplète ! Veuillez renseigner : {', '.join(missing)}", 'error')
        return redirect('/settings')

def get_qbit_session():
    session = requests.Session()
    # On s'assure que l'URL n'a pas de slash à la fin pour éviter //api
    qb_url = CONFIG['QB_URL'].rstrip('/')
    try:
        session.post(f"{qb_url}/api/v2/auth/login", data={'username': CONFIG['QB_USER'], 'password': CONFIG['QB_PASS']}, timeout=5)
    except requests.exceptions.RequestException:
        pass # L'erreur sera gérée plus tard si la requête échoue
    return session

def clean_name(name):
    name = re.sub(r'\[.*?\]', '', name)
    name = name.replace('.', ' ').replace('_', ' ')
    name = re.sub(r'(1080p|720p|WEB-DL|x264|x265|Bluray|VFF|FRENCH|MULTi|Fiv|TrueFrench|DVDRIP|BDRIP).*', '', name, flags=re.I)
    return name.strip()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/settings')
def settings():
    return render_template('settings.html', config=CONFIG)

@app.route('/settings/update', methods=['POST'])
def update_settings():
    global CONFIG
    
    # Fonction locale pour nettoyer les entrées du formulaire
    def get_clean_val(key):
        val = request.form.get(key, "")
        if val:
            val = val.strip()
            # Si c'est une URL, on enlève le slash final
            if key.endswith('_URL'):
                val = val.rstrip('/')
        return val

    new_config = {
        "QB_URL": get_clean_val('QB_URL'),
        "JACKETT_URL": get_clean_val('JACKETT_URL'),
        "QB_USER": get_clean_val('QB_USER'),
        "QB_PASS": get_clean_val('QB_PASS'),
        "TMDB_KEY": get_clean_val('TMDB_KEY'),
        "OMDB_KEY": get_clean_val('OMDB_KEY'),
        "JACKETT_API_KEY": get_clean_val('JACKETT_API_KEY')
    }
    
    save_config(new_config)
    CONFIG = new_config
    
    flash('Configuration enregistrée avec succès !', 'success')
    return redirect('/settings')


@app.route('/gestion')
def gestion():
    try:
        session = get_qbit_session()
        qb_url = CONFIG['QB_URL'].rstrip('/')
        resp = session.get(f"{qb_url}/api/v2/torrents/info", timeout=5)
        resp.raise_for_status() # Lève une erreur si la réponse n'est pas 200 OK
        
        torrents = resp.json()
        films = [t for t in torrents if t.get('category') == 'films']
        series = [t for t in torrents if t.get('category') == 'series']
        
        for t in films + series:
            t['clean_name'] = clean_name(t.get('name', ''))
            
        return render_template('gestion.html', films=films, series=series)
    except Exception as e:
        return render_template('base.html', content=f"<div class='container'><h2>Erreur de connexion</h2><p>Impossible de contacter qBittorrent. Vérifiez l'URL et vos identifiants dans les réglages.</p><p>Détail: {e}</p><a href='/settings' class='btn-action btn-danger'>Aller aux réglages</a></div>")

@app.route('/add', methods=['POST'])
def add_torrent():
    magnet_link = request.form.get('magnet')
    category = request.form.get('category') # 'films' ou 'series'
    session = get_qbit_session()
    
    save_path = f"/home/timofei/downloads/{category}"
    qb_url = CONFIG['QB_URL'].rstrip('/')
    
    payload = {
        'urls': magnet_link, 
        'category': category, 
        'savepath': save_path
    }
    try:
        session.post(f"{qb_url}/api/v2/torrents/add", data=payload)
    except:
        flash("Erreur lors de l'ajout du torrent", "error")
        
    return redirect('/gestion')

@app.route('/delete/<hash>')
def delete_torrent(hash):
    session = get_qbit_session()
    qb_url = CONFIG['QB_URL'].rstrip('/')
    try:
        session.post(f"{qb_url}/api/v2/torrents/delete", data={'hashes': hash, 'deleteFiles': 'true'})
    except:
        flash("Erreur lors de la suppression", "error")
    return redirect('/gestion')

@app.route('/restart_service', methods=['POST'])
def restart_service():
    os.system('sudo systemctl restart netflixos')
    return redirect('/settings')

@app.route('/shutdown_server', methods=['POST'])
def shutdown_server():
    os.system('sudo shutdown now')
    return "<h1>Extinction du serveur en cours...</h1>"

@app.route('/search')
def search():
    query = request.args.get('q')
    results = []
    if query:
        jackett_url = CONFIG['JACKETT_URL'].rstrip('/')
        url = f"{jackett_url}/api/v2.0/indexers/all/results?apikey={CONFIG['JACKETT_API_KEY']}&Query={query}"
        try:
            r = requests.get(url, timeout=10)
            if r.status_code == 200:
                results = r.json().get('Results', [])
        except:
            pass
    return render_template('search.html', results=results)

@app.route('/get_info')
def get_info():
    raw_title = request.args.get('title')
    if not raw_title:
        return jsonify({"error": "Titre manquant"})
        
    title = clean_name(raw_title)
    tmdb_key = CONFIG['TMDB_KEY']
    
    tmdb_url = f"https://api.themoviedb.org/3/search/movie?api_key={tmdb_key}&query={title}&language=fr-FR"
    try:
        data = requests.get(tmdb_url, timeout=5).json()
        if data.get('results'):
            movie_id = data['results'][0]['id']
            detail_url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={tmdb_key}&append_to_response=credits,videos&language=fr-FR"
            movie = requests.get(detail_url, timeout=5).json()
            return jsonify({
                "poster": f"https://image.tmdb.org/t/p/w500{movie.get('poster_path')}" if movie.get('poster_path') else "",
                "description": movie.get('overview', 'Pas de description.'),
                "cast": ", ".join([c['name'] for c in movie.get('credits', {}).get('cast', [])[:5]]),
                "trailer": next((f"https://www.youtube.com/embed/{v['key']}" for v in movie.get('videos', {}).get('results', []) if v['site'] == 'YouTube' and v['type'] == 'Trailer'), "")
            })
        
        # Secours OMDB si TMDB ne trouve rien
        omdb_key = CONFIG['OMDB_KEY']
        omdb_url = f"http://www.omdbapi.com/?t={title}&apikey={omdb_key}"
        omdb_data = requests.get(omdb_url, timeout=5).json()
        return jsonify({"poster": omdb_data.get('Poster'), "description": omdb_data.get('Plot'), "cast": omdb_data.get('Actors')})
    except:
        return jsonify({"error": "Non trouvé"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
