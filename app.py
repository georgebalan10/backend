from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_mail import Mail, Message
from models import db, User, Appointment, Review, Upload,AIQuestion
from datetime import datetime
import os
from werkzeug.utils import secure_filename
from flask import send_from_directory
import sqlite3
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
import difflib
from whoosh import index
from whoosh.fields import Schema, TEXT
from whoosh.qparser import QueryParser,OrGroup
from collections import Counter
import json

app = Flask(__name__)
CORS(app)

load_dotenv()

# Configurare bază de date
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False


DATABASE = os.path.join('instance', 'database.db')

# Configurare Flask-Mail
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'acupunctura.contact@gmail.com'  # contul tău Gmail
app.config['MAIL_PASSWORD'] = 'znmbjslwrupycdyh'        # parola generată aplicație

mail = Mail(app)
db.init_app(app)

with app.app_context():
    db.create_all()


#config poze
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # max 16MB

def build_index():
    schema = Schema(content=TEXT(stored=True))
    if not os.path.exists("indexdir"):
        os.mkdir("indexdir")
    ix = index.create_in("indexdir", schema)
    writer = ix.writer()

    sources = [
        "https://ro.wikipedia.org/wiki/Acupunctur%C4%83",
        "https://www.mayoclinic.org/tests-procedures/acupuncture/about/pac-20392763",
        "https://www.webmd.com/balance/guide/acupuncture-therapy",
        "https://acupuncture.org.uk/about-acupuncture/what-is-acupuncture/",
        "https://www.healthline.com/health/acupuncture",
        "https://www.betterhealth.vic.gov.au/health/conditionsandtreatments/acupuncture",
        "https://www.nhs.uk/conditions/acupuncture/",
        "https://www.verywellhealth.com/acupuncture-overview-89715",
        "https://my.clevelandclinic.org/health/treatments/21050-acupuncture"
    ]

    for url in sources:
        try:
            print(f"🔄 Descarc: {url}")
            res = requests.get(url, timeout=20)
            soup = BeautifulSoup(res.text, 'html.parser')
            paragraphs = soup.find_all('p')
            for p in paragraphs:
                text = p.get_text().strip()
                if len(text) > 50:  # salvăm doar paragrafele utile
                    writer.add_document(content=text)
        except Exception as e:
            print(f"⚠️ Eroare la {url}: {str(e)}")
    writer.commit()
    print("✅ Index creat cu succes!")


@app.route("/")
def home():
    return "API-ul funcționează!"

@app.route("/api/register", methods=["POST"])
def register():
    data = request.get_json()
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")

    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({"message": "Email deja înregistrat"}), 409

    new_user = User(name=name, email=email, password=password)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "Utilizator înregistrat cu succes"}), 201

@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()

    user = User.query.filter_by(email=email).first()

    if user and user.password == password:
        return jsonify({
            "message": "Autentificare reușită",
            "user": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "is_admin": user.is_admin
            }
        }), 200
    else:
        return jsonify({"message": "Email sau parolă incorecte"}), 401

@app.route("/api/appointments", methods=["POST"])
def create_appointment():
    data = request.get_json()
    user_id = data.get("user_id")
    message = data.get("message")
    date = data.get("date")
    time = data.get("time")

    existing = Appointment.query.filter_by(date=date, time=time).first()
    if existing:
        return jsonify({"message": "Ora este deja rezervată!"}), 409

    appointment = Appointment(user_id=user_id, message=message, date=date, time=time)
    db.session.add(appointment)
    db.session.commit()

    return jsonify({"message": "Rezervare adăugată cu succes"}), 201

@app.route("/api/appointments/<int:user_id>", methods=["GET"])
def get_appointments_for_user(user_id):
    appointments = Appointment.query.filter_by(user_id=user_id).all()
    result = [{
        "id": a.id,
        "message": a.message,
        "date": a.date,
        "time": a.time,
        "confirmed": a.confirmed,
        "duration_minutes": a.duration_minutes
    } for a in appointments]
    return jsonify({"appointments": result}), 200

@app.route("/api/admin/appointments", methods=["GET"])
def get_all_appointments():
    appointments = Appointment.query.all()
    result = [{
        "id": a.id,
        "user_id": a.user_id,
        "user_name": a.user.name,
        "message": a.message,
        "date": a.date,
        "time": a.time,
        "confirmed": a.confirmed,
        "duration_minutes": a.duration_minutes
    } for a in appointments]
    return jsonify({"appointments": result}), 200

@app.route("/api/admin/appointments/<int:id>", methods=["PUT"])
def confirm_appointment(id):
    data = request.get_json()
    duration = data.get("duration_minutes")

    if duration is None:
        return jsonify({"message": "Trebuie să selectați durata rezervării!"}), 400

    appointment = Appointment.query.get(id)
    if not appointment:
        return jsonify({"message": "Rezervarea nu există"}), 404

    appointment.confirmed = True
    appointment.duration_minutes = duration
    db.session.commit()
    return jsonify({"message": "Rezervarea a fost confirmată"}), 200

@app.route("/api/appointments/<int:appointment_id>", methods=["DELETE"])
def delete_appointment(appointment_id):
    appointment = Appointment.query.get_or_404(appointment_id)
    db.session.delete(appointment)
    db.session.commit()
    return jsonify({"message": "Rezervare ștearsă cu succes!"}), 200

@app.route("/api/reviews", methods=["POST"])
def create_review():
    data = request.get_json()
    user_id = data.get("user_id")
    text = data.get("content")
    rating = data.get("rating")
    today = datetime.today().strftime('%Y-%m-%d')

    review = Review(user_id=user_id, text=text, rating=rating, date=today)
    db.session.add(review)
    db.session.commit()
    return jsonify({"message": "Review adăugat cu succes"}), 201

@app.route("/api/reviews/<int:user_id>", methods=["GET"])
def get_reviews_by_user(user_id):
    reviews = Review.query.filter_by(user_id=user_id).all()
    result = [{
        "id": r.id,
        "text": r.text,
        "rating": r.rating,
        "date": r.date
    } for r in reviews]
    return jsonify({"reviews": result}), 200

@app.route("/api/admin/reviews", methods=["GET"])
def get_all_reviews():
    reviews = Review.query.all()
    result = [{
        "id": r.id,
        "text": r.text,
        "date": r.date,
        "user_id": r.user_id,
        "user_name": r.user.name,
        "rating": r.rating
    } for r in reviews]
    return jsonify({"reviews": result}), 200

# Trimitere email din formular contact
@app.route("/api/send-email", methods=["POST"])
def send_email():
    data = request.get_json()
    name = data.get("name")
    email = data.get("email")
    subject = data.get("subject")
    message = data.get("message")

    try:
        msg = Message(subject,
                      sender=email,
                      recipients=['acupunctura.contact@gmail.com'])
        msg.body = f"Mesaj de la: {name} <{email}>\n\n{message}"
        mail.send(msg)
        return jsonify({"message": "Email trimis cu succes!"}), 200
    except Exception as e:
        return jsonify({"message": "Eroare la trimiterea emailului.", "error": str(e)}), 500


@app.route("/api/user/<int:user_id>/update", methods=["PUT"])
def update_user_data(user_id):
    data = request.get_json()
    new_email = data.get("email")
    new_password = data.get("password")

    user = User.query.get(user_id)
    if not user:
        return jsonify({"message": "Utilizatorul nu a fost găsit"}), 404

    # Verificăm dacă emailul e deja folosit de altcineva
    if new_email and new_email != user.email:
        email_taken = User.query.filter_by(email=new_email).first()
        if email_taken:
            return jsonify({"message": "Emailul este deja folosit de alt utilizator"}), 409
        user.email = new_email

    if new_password:
        user.password = new_password

    db.session.commit()
    return jsonify({"message": "Datele au fost actualizate cu succes"}), 200

@app.route("/api/uploads", methods=["POST"])
def upload_images():
    user_id = request.form.get("user_id")
    if not user_id:
        return jsonify({"message": "Lipsește user_id"}), 400

    files = request.files.getlist("images")
    index = 0
    for file in files:
        if file.filename == "":
            continue
        filename = secure_filename(file.filename)
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(path)

        desc = request.form.get(f"desc_{index}", "")
        upload = Upload(user_id=user_id, filename=filename, description=desc)
        db.session.add(upload)
        index += 1

    db.session.commit()
    return jsonify({"message": "Upload complet!"}), 201

@app.route("/api/uploads/user/<int:user_id>", methods=["GET"])
def get_user_uploads(user_id):
    uploads = Upload.query.filter_by(user_id=user_id).all()
    results = [{
        "filename": u.filename,
        "description": u.description
    } for u in uploads]
    return jsonify({"uploads": results}), 200

@app.route("/api/uploads/all", methods=["GET"])
def get_all_uploads_summary():
    users = User.query.all()
    data = []
    for user in users:
        count = Upload.query.filter_by(user_id=user.id).count()
        if count > 0:
            data.append({
                "user_id": user.id,
                "name": user.name,
                "email": user.email,
                "count": count
            })
    return jsonify({"summary": data}), 200

@app.route("/uploads/<filename>")
def serve_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route("/api/uploads", methods=["GET"])
def get_all_uploads():
    uploads = Upload.query.all()
    result = {}

    for u in uploads:
        if u.user.name not in result:
            result[u.user.name] = []
        result[u.user.name].append({
            "id": u.id,
            "filename": u.filename,
            "description": u.description
        })

    summarized = [{"user": name, "count": len(files)} for name, files in result.items()]
    return jsonify({"uploads": summarized}), 200

@app.route("/api/uploads/by-user/<int:user_id>", methods=["GET"])
def get_uploads_by_user(user_id):
    uploads = Upload.query.filter_by(user_id=user_id).all()
    result = [{
        "id": u.id,
        "filename": u.filename,
        "description": u.description
    } for u in uploads]
    return jsonify({"uploads": result}), 200
@app.route("/api/uploads/<int:upload_id>", methods=["DELETE"])
def delete_upload(upload_id):
    upload = Upload.query.get(upload_id)
    if not upload:
        return jsonify({"message": "Imaginea nu a fost găsită"}), 404

    # Șterge fișierul de pe disc
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], upload.filename)
    if os.path.exists(file_path):
        os.remove(file_path)

    # Șterge înregistrarea din baza de date
    db.session.delete(upload)
    db.session.commit()
    return jsonify({"message": "Imagine ștearsă cu succes"}), 200


@app.route('/appointments_full/<int:user_id>', methods=['GET'])
def get_appointments_full(user_id):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, user_id, message, date, time, duration, confirmed, duration_minutes
        FROM appointment
        WHERE user_id = ?
    """, (user_id,))
    appointments = cursor.fetchall()
    conn.close()

    result = []
    for appt in appointments:
        result.append({
            'id': appt[0],
            'user_id': appt[1],
            'message': appt[2],
            'date': appt[3],
            'time': appt[4],  # ADĂUGAT!
            'duration': appt[5],
            'confirmed': bool(appt[6]),
            'duration_minutes': appt[7]
        })
    return jsonify(result)

@app.route('/api/chatbot', methods=['POST'])
def chatbot():
    data = request.get_json()
    user_message = data.get('message', '').strip()
    user_id = data.get('user_id')  # Asigură-te că frontend-ul trimite și user_id!

    if not user_message:
        return jsonify({'reply': 'Nu am înțeles întrebarea ta.'})

    # Salvăm întrebarea în baza de date
    new_question = AIQuestion(user_id=user_id, text=user_message)
    db.session.add(new_question)
    db.session.commit()

    # Căutăm răspuns cu Whoosh
    ix = index.open_dir("indexdir")
    with ix.searcher() as searcher:
        parser = QueryParser("content", ix.schema, group=OrGroup.factory(0.9))
        query = parser.parse(user_message)
        results = searcher.search(query, limit=2)
        if results:
            reply_text = results[0]['content']
        else:
            reply_text = "Îmi pare rău, nu am găsit un răspuns clar la întrebarea ta."

    return jsonify({'reply': reply_text})

@app.route('/api/admin/ai-question-stats', methods=['GET'])
def ai_question_stats():
    results = db.session.query(
        AIQuestion.text,
        db.func.count(AIQuestion.text).label('count')
    ).group_by(AIQuestion.text).order_by(db.desc('count')).limit(10).all()

    top_10 = [{'question': r.text, 'count': r.count} for r in results]
    return jsonify({'stats': top_10})

@app.route('/api/admin/rebuild-index', methods=['POST'])
def rebuild_index():
    try:
        build_index()
        return jsonify({"message": "Index reconstruit cu succes!"}), 200
    except Exception as e:
        return jsonify({"message": f"Eroare: {str(e)}"}), 500

@app.route('/api/admin/reset-ai-questions', methods=['POST'])
def reset_ai_questions():
    AIQuestion.query.delete()
    db.session.commit()
    return jsonify({'message': 'Toate întrebările au fost șterse!'}), 200

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
        # build_index()  # <-- corectat cu spații

