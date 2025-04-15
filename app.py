
# 1070657144197-jdv61agehj4bk817tsenk15pa0qkhlf6.apps.googleusercontent.com',  # Vervang door je eigen Client ID
# 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',  # Vervang door je eigen Client Secret


# app.py

import os
from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin, current_user
from flask_dance.contrib.google import make_google_blueprint, google
from flask_dance.consumer import oauth_authorized
from sqlalchemy import Integer, String, Boolean, ForeignKey
from sqlalchemy.ext.mutable import MutableDict

app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///videos.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = os.getenv('SECRET_KEY', 'een_tijdelijke_geheime_sleutel')
app.config['GOOGLE_OAUTH_CLIENT_ID'] = os.getenv('GOOGLE_OAUTH_CLIENT_ID')
app.config['GOOGLE_OAUTH_CLIENT_SECRET'] = os.getenv('GOOGLE_OAUTH_CLIENT_SECRET')

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'google.login'

# Modellen
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)

class Technique(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    category = db.Column(db.String(100), nullable=False, default="tachiwaza")

class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    youtube_url = db.Column(db.String(255), nullable=False)
    embedded_url = db.Column(db.String(255), nullable=False)
    technique_id = db.Column(db.Integer, ForeignKey('technique.id'), nullable=False)
    votes = db.Column(MutableDict.as_mutable(db.JSON), nullable=False, default=lambda: {})
    average_rating = db.Column(db.Float, nullable=False, default=0.0)
    labels = db.Column(db.JSON, nullable=False, default=lambda: [])  # Blijft hetzelfde

# Google OAuth
google_bp = make_google_blueprint(
    client_id='1070657144197-jdv61agehj4bk817tsenk15pa0qkhlf6.apps.googleusercontent.com',  # Vervang door je eigen Client ID
    client_secret='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',  # Vervang door je eigen Client Secret
    scope=["openid", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile"],
    redirect_url='/google_login/google/authorized'
)
app.register_blueprint(google_bp, url_prefix='/google_login')

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

@oauth_authorized.connect_via(google_bp)
def google_logged_in(blueprint, token):
    if not token:
        return False
    resp = google.get('/oauth2/v2/userinfo')
    if not resp.ok:
        return False
    user_info = resp.json()
    email = user_info.get('email')
    if not email:
        return False
    user = User.query.filter_by(email=email).first()
    if user is None:
        user = User(email=email, name=user_info.get('name', 'Onbekend'))
        db.session.add(user)
        db.session.commit()
    login_user(user)
    return redirect(url_for('home'))

# Routes
@app.route('/')
def home():
    if not current_user.is_authenticated:
        return redirect(url_for('google.login'))
    return render_template('home.html')

@app.route('/tachiwaza')
@login_required
def tachiwaza():
    techniques = Technique.query.filter_by(category="tachiwaza").all()
    return render_template('tachiwaza.html', techniques=techniques)

@app.route('/newaza')
@login_required
def newaza():
    techniques = Technique.query.filter_by(category="newaza").all()
    return render_template('newaza.html', techniques=techniques)

@app.route('/exercises', methods=['GET', 'POST'])
@login_required
def exercises():
    # Zoek of maak de "Exercises & games" techniek
    tech = Technique.query.filter_by(name="Exercises & games").first()
    if not tech:
        tech = Technique(name="Exercises & games", category="exercises")
        db.session.add(tech)
        db.session.commit()

    if request.method == 'POST':
        youtube_url = request.form.get('youtube_url')
        labels_input = request.form.get('labels', '')
        print(f"Received youtube_url: {youtube_url}")
        print(f"Received labels: {labels_input}")
        if not youtube_url:
            return "Geen YouTube URL opgegeven", 400
        if "youtube.com/watch?v=" not in youtube_url and "youtu.be/" not in youtube_url:
            return f"Ongeldige YouTube URL: {youtube_url}", 400
        video_id = youtube_url.split("v=")[-1].split("&")[0] if "v=" in youtube_url else youtube_url.split("/")[-1]
        embedded_url = f"https://www.youtube.com/embed/{video_id}"
        labels = [label.strip() for label in labels_input.split(',') if label.strip()] if labels_input else []
        new_video = Video(youtube_url=youtube_url, embedded_url=embedded_url, technique_id=tech.id, labels=labels)
        try:
            db.session.add(new_video)
            db.session.commit()
            return redirect(url_for('exercises'))
        except Exception as e:
            db.session.rollback()
            return f"Fout bij toevoegen video: {str(e)}", 500

    search_query = request.args.get('search', '').lower()
    videos = Video.query.filter_by(technique_id=tech.id).all()
    if search_query:
        videos = [v for v in videos if any(search_query in label.lower() for label in v.labels)]
    
    videos = sorted(videos, key=lambda v: v.average_rating if v.average_rating is not None else 0, reverse=True)

    videos_with_status = [
        {'video': video, 'has_voted': str(current_user.id) in video.votes}
        for video in videos
    ]

    return render_template('exercises.html', videos_with_status=videos_with_status, search_query=search_query)

@app.route('/tachiwaza/<technique>', methods=['GET', 'POST'])
@login_required
def technique_page(technique):
    tech = Technique.query.filter_by(name=technique).first()
    if not tech:
        tech = Technique(name=technique, category="tachiwaza")
        db.session.add(tech)
        db.session.commit()

    if request.method == 'POST':
        youtube_url = request.form.get('youtube_url')
        labels_input = request.form.get('labels', '')
        print(f"Received youtube_url: {youtube_url}")
        print(f"Received labels: {labels_input}")
        if not youtube_url:
            return "Geen YouTube URL opgegeven", 400
        if "youtube.com/watch?v=" not in youtube_url and "youtu.be/" not in youtube_url:
            return f"Ongeldige YouTube URL: {youtube_url}", 400
        video_id = youtube_url.split("v=")[-1].split("&")[0] if "v=" in youtube_url else youtube_url.split("/")[-1]
        embedded_url = f"https://www.youtube.com/embed/{video_id}"
        labels = [label.strip() for label in labels_input.split(',') if label.strip()] if labels_input else []
        new_video = Video(youtube_url=youtube_url, embedded_url=embedded_url, technique_id=tech.id, labels=labels)
        try:
            db.session.add(new_video)
            db.session.commit()
            return redirect(url_for('technique_page', technique=technique))
        except Exception as e:
            db.session.rollback()
            return f"Fout bij toevoegen video: {str(e)}", 500

    search_query = request.args.get('search', '').lower()
    videos = Video.query.filter_by(technique_id=tech.id).all()
    if search_query:
        videos = [v for v in videos if any(search_query in label.lower() for label in v.labels)]
    
    # Sorteer video's op average_rating, van hoog naar laag
    videos = sorted(videos, key=lambda v: v.average_rating if v.average_rating is not None else 0, reverse=True)

    videos_with_status = [
        {'video': video, 'has_voted': str(current_user.id) in video.votes}
        for video in videos
    ]

    return render_template('tachiwaza/technique.html', technique=technique, videos_with_status=videos_with_status, search_query=search_query)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

@app.route('/vote/tachiwaza/<technique>', methods=['POST'])
@login_required
def vote_technique(technique):
    # Controleer of de techniek bestaat
    tech = Technique.query.filter_by(name=technique).first()
    if not tech:
        return jsonify({'error': 'Techniek niet gevonden'}), 404

    # Haal de JSON-data uit het request
    data = request.get_json()
    video_id = data.get('video_id')
    rating = data.get('rating')

    if not video_id or not rating:
        return jsonify({'error': 'Video ID of rating ontbreekt'}), 400

    # Zoek het video-object
    video = Video.query.get(video_id)
    if not video or video.technique_id != tech.id:
        return jsonify({'error': 'Video niet gevonden of hoort niet bij deze techniek'}), 404

    # Controleer of de gebruiker al heeft gestemd
    user_id = str(current_user.id)
    if user_id in video.votes:
        return jsonify({'error': 'Je hebt al gestemd op deze video'}), 403

    # Voeg de stem toe aan de votes-dictionary
    video.votes[user_id] = rating
    db.session.commit()

    # Bereken het nieuwe gemiddelde en totaal aantal stemmen
    total_votes = len(video.votes)
    average_rating = sum(float(vote) for vote in video.votes.values()) / total_votes if total_votes > 0 else 0.0
    video.average_rating = average_rating
    db.session.commit()

    # Stuur de response terug naar de frontend
    return jsonify({
        'average_rating': round(average_rating, 1),
        'total_votes': total_votes
    })

# Nieuwe route voor Exercises & games
@app.route('/vote/exercises', methods=['POST'])
@login_required
def vote_exercises():
    tech = Technique.query.filter_by(name="Exercises & games").first()
    if not tech:
        return jsonify({'error': 'Techniek niet gevonden'}), 404

    data = request.get_json()
    video_id = data.get('video_id')
    rating = data.get('rating')

    if not video_id or not rating:
        return jsonify({'error': 'Video ID of rating ontbreekt'}), 400

    video = Video.query.get(video_id)
    if not video or video.technique_id != tech.id:
        return jsonify({'error': 'Video niet gevonden of hoort niet bij deze techniek'}), 404

    user_id = str(current_user.id)
    if user_id in video.votes:
        return jsonify({'error': 'Je hebt al gestemd op deze video'}), 403

    video.votes[user_id] = rating
    db.session.commit()

    total_votes = len(video.votes)
    average_rating = sum(float(vote) for vote in video.votes.values()) / total_votes if total_votes > 0 else 0.0
    video.average_rating = average_rating
    db.session.commit()

    return jsonify({
        'average_rating': round(average_rating, 1),
        'total_votes': total_votes
    })

    
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        techniques = [
            "O-soto-gari", "De-ashi-barai", "Okuri-ashi-barai", "Hiza-guruma", "Ko-soto-gake",
            "O-uchi-gari", "Ko-uchi-gari", "O-soto-guruma", "O-soto-otoshi", "Ko-soto-gari",
            "Sasae-tsuri-komi-ashi", "Harai-tsuri-komi-ashi", "O-soto-gake", "Ko-uchi-maki-komi",
            "Ashi-guruma", "Uchi-mata", "Uki-goshi", "Kubi-nage", "Tsuri-goshi", "Koshi-guruma",
            "Harai-goshi", "Hane-goshi", "Ushiro-goshi", "Tsuri-komi-goshi", "Utsuri-goshi",
            "O-goshi", "Ko-tsuri-goshi", "O-guruma", "Yama-arashi", "Obi-goshi", "Kata-seoi",
            "Ippon-seoi-nage", "Kata-guruma", "Seoi-otoshi", "Hidari-kata-seoi", "Morote-seoi-nage",
            "Eri-seoi-nage", "Tai-otoshi", "Uki-otoshi", "Sokui-nage", "Kata-ashi-dori", "Ryo-ashi-dori",
            "Tomoe-nage", "Yoko-tomoe-nage", "Soto-maki-komi", "Yoko-gake", "Tani-otoshi", "Sumi-gaeshi",
            "Kani-basami", "Ura-nage", "Yoko-guruma", "Ude-hishigi-juji-katame", "Ude-garami", "Ude-hishigi",
            "Yoko-hiza-katame", "Kami-ude-hishigi-juji-katame", "Yoko-ude-hishigi", "Kami-hiza-katame",
            "Ude-hishigi-henka-waza", "Gyaku-juji", "Shime-garami", "Hiza-katame", "Hara-katame",
            "Ashi-katame", "Ude-garami-henka-waza", "Kesa-garami", "Kuzure-kami-shiho-garami",
            "Gyaku-kesa-garami", "Gyaku-te-kubi", "Hiji-maki-komi", "Kanuki-katame", "Ude-hishigi-hiza-katame",
            "Kata-juji-jime", "Name-juji-jime", "Gyaku-juji-jime", "Yoko-juji-jime", "Ushiro-jime",
            "Okuri-eri-jime", "Kata-ha-jime", "Hadaka-jime", "Ebi-garami", "Tomoe-jime", "Narabi-juji-jime",
            "Katate-jime", "Sode-guruma", "Hidari-ashi-jime", "Kagato-jime", "Kami-shiho-jime",
            "Kami-shiho-ashi-jime", "Kami-shiho-basami", "Gyaku-okuri-eri", "Gaeshi-jime",
            "Gyaku-gaeshi-jime", "Kesa-katame", "Kata-katame", "Kami-shiho-katame",
            "Kuzure-kami-shiho-katame", "Ushiro-kesa-gatame", "Gyaku-kesa-katame", "Yoko-shiho-katame",
            "Makura-kesa-katame", "Mune-katame", "Tate-shiho-katame", "Kuzure-kesa-katame",
            "Kata-osae-katame", "Ura-katame", "Kashira-katame", "Ura-shiho-katame", "Kami-sankaku-katame",
            "Kuzure-yoko-shiho", "Tate-sankaku-katame", "Uki-katame"
        ]
        if not Technique.query.filter_by(name="Exercises & games").first():
            db.session.add(Technique(name="Exercises & games", category="exercises"))
        db.session.commit()
    port = int(os.getenv("PORT", 5000))  # Gebruik Render's poort, fallback naar 5000 lokaal
    app.run(host="0.0.0.0", port=port, debug=False)

from flask import send_from_directory

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static/images'), 'blackbelt.webp', mimetype='image/webp')