import os
import re
import requests
from flask import Flask, request, render_template, redirect, jsonify

app = Flask(__name__)

# --- CONFIGURATION (Via Variables d'Environnement Docker) ---
QB_URL = "http://qbittorrent:8080"
JACKETT_URL = "http://jackett:9117"
QB_USER = "admin"
QB_PASS = os.getenv('QB_PASS')
TMDB_KEY = os.getenv('TMDB_KEY')
OMDB_KEY = os.getenv('OMDB_KEY')
JACKETT_API_KEY = os.getenv('JACKETT_KEY')

def get_qbit_session():
    session = requests.Session()
    session.post(f"{QB_URL}/api/v2/auth/login", data={'username': QB_USER, 'password': QB_PASS})
    return session

def clean_name(name):
    name = re.sub(r'\[.*?\]', '', name)
    name = name.replace('.', ' ').replace('_', ' ')
    name = re.sub(r'(1080p|720p|WEB-DL|x264|x265|Bluray|VFF|FRENCH|MULTi|Fiv|TrueFrench|DVDRIP|BDRIP).*', '', name, flags=re.I)
    return name.strip()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/gestion')
def gestion():
    try:
        session = get_qbit_session()
        resp = session.get(f"{QB_URL}/api/v2/torrents/info")
        torrents = resp.json()
        films = [t for t in torrents if t['category'] == 'films']
        series = [t for t in torrents if t['category'] == 'series']
        for t in films + series:
            t['clean_name'] = clean_name(t['name'])
        return render_template('gestion.html', films=films, series=series)
    except:
        return "Erreur : Vérifiez que qBittorrent est lancé et le mot de passe configuré."

@app.route('/add', methods=['POST'])
def add_torrent():
    magnet_link = request.form.get('magnet')
    category = request.form.get('category') # 'films' ou 'series'
    session = get_qbit_session()
    
    # On force le dossier Docker partagé
    save_path = f"/media/{category}"
    
    payload = {
        'urls': magnet_link, 
        'category': category, 
        'savepath': save_path
    }
    session.post(f"{QB_URL}/api/v2/torrents/add", data=payload)
    return redirect('/gestion')

@app.route('/delete/<hash>')
def delete_torrent(hash):
    session = get_qbit_session()
    session.post(f"{QB_URL}/api/v2/torrents/delete", data={'hashes': hash, 'deleteFiles': 'true'})
    return redirect('/gestion')

@app.route('/search')
def search():
    query = request.args.get('q')
    results = []
    if query:
        url = f"{JACKETT_URL}/api/v2.0/indexers/all/results?apikey={JACKETT_API_KEY}&Query={query}"
        try:
            r = requests.get(url)
            results = r.json().get('Results', [])
        except:
            pass
    return render_template('search.html', results=results)

@app.route('/get_info')
def get_info():
    raw_title = request.args.get('title')
    title = clean_name(raw_title)
    tmdb_url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_KEY}&query={title}&language=fr-FR"
    try:
        data = requests.get(tmdb_url).json()
        if data.get('results'):
            movie_id = data['results'][0]['id']
            detail_url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_KEY}&append_to_response=credits,videos&language=fr-FR"
            movie = requests.get(detail_url).json()
            return jsonify({
                "poster": f"https://image.tmdb.org/t/p/w500{movie.get('poster_path')}" if movie.get('poster_path') else "",
                "description": movie.get('overview', 'Pas de description.'),
                "cast": ", ".join([c['name'] for c in movie.get('credits', {}).get('cast', [])[:5]]),
                "trailer": next((f"https://www.youtube.com/embed/{v['key']}" for v in movie.get('videos', {}).get('results', []) if v['site'] == 'YouTube' and v['type'] == 'Trailer'), "")
            })
        # Secours OMDB
        omdb_url = f"http://www.omdbapi.com/?t={title}&apikey={OMDB_KEY}"
        omdb_data = requests.get(omdb_url).json()
        return jsonify({"poster": omdb_data.get('Poster'), "description": omdb_data.get('Plot'), "cast": omdb_data.get('Actors')})
    except:
        return jsonify({"error": "Non trouvé"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
