
# Standardbibliotheken und Flask-Module importieren
import os
from flask import Flask, jsonify, request  # Flask-Anwendung, JSON-Antworten und Request-Objekt
from flask_migrate import Migrate  # Für Datenbankmigrationen
from dotenv import load_dotenv  # Für das Laden von Umgebungsvariablen aus .env-Dateien
from models import db, Topic, Skill  # Datenbankmodelle importieren
from sqlalchemy import exists  # Für Abfragen, ob abhängige Einträge existieren


# Lädt Umgebungsvariablen aus einer .env-Datei, falls vorhanden
load_dotenv()


# Initialisiere die Flask-App
app = Flask(__name__)

# Konfiguriere die Datenbankverbindung (nutzt Umgebungsvariable oder Default)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://app:app123@localhost:5432/topics_db"
)
# Deaktiviere das SQLAlchemy-Tracking, um Overhead zu vermeiden
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialisiere die Datenbank und Migrationstools
db.init_app(app)
Migrate(app, db)



# Basis-Endpunkt zur Überprüfung, ob der Service läuft
@app.route('/')
def hello_world():
    """
    Gibt eine einfache Nachricht zurück, um die Erreichbarkeit des Services zu testen.
    """
    return 'Hello from Topic & Skill Service!'


# Health-Check-Endpunkt für Monitoring/Loadbalancer
@app.get("/healthz")
def healthz():
    """
    Gibt den Status des Services zurück (z.B. für Monitoring).
    """
    return {"status": "ok"}


# =====================
#   TOPIC ENDPUNKTE
# =====================


# Gibt alle Topics als Liste zurück
@app.route('/topics', methods=['GET'])
def get_topics():
    """
    Ruft alle verfügbaren Lern-Topics aus der Datenbank ab und gibt sie als Liste zurück.
    """
    rows = Topic.query.order_by(Topic.name.asc()).all()
    data = [topic.to_dict() for topic in rows]
    return jsonify(data)


# Gibt ein einzelnes Topic anhand der ID zurück
@app.route('/topics/<id>', methods=['GET'])
def get_topic_by_id(id):
    """
    Ruft ein einzelnes Lern-Topic anhand seiner ID ab.
    Gibt 404 zurück, wenn das Topic nicht existiert.
    """
    topic = Topic.query.get(id)
    if not topic:
        return jsonify({"error": "Topic not found"}), 404
    return topic.to_dict()


# Legt ein neues Topic an
@app.route('/topics', methods=['POST'])
def create_topic():
    """
    Erstellt ein neues Lern-Topic.
    Erwartet 'name' und optional 'description' und 'parentTopicID' im JSON-Body.
    Prüft, ob das Parent-Topic existiert.
    """
    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    description = payload.get("description")
    parent_id = payload.get("parentTopicID")

    if not name:
        return jsonify({"error": "Field 'name' is required."}), 422

    # Prüfe, ob das Parent-Topic existiert (falls angegeben)
    if parent_id:
        parent = Topic.query.get(parent_id)
        if not parent:
            return jsonify({"error": "parentTopicID not found"}), 422

    topic = Topic(name=name, description=description, parent_topic_id=parent_id)
    db.session.add(topic)
    db.session.commit()
    return topic.to_dict(), 201


# Aktualisiert ein bestehendes Topic anhand der ID
@app.route('/topics/<id>', methods=['PUT'])
def update_topic(id):
    """
    Aktualisiert ein bestehendes Lern-Topic anhand seiner ID.
    Erwartet 'name', 'description' und optional 'parentTopicID' im JSON-Body.
    Prüft, ob das Parent-Topic existiert.
    """
    topic = Topic.query.get(id)
    if not topic:
        return jsonify({"error": "Topic not found"}), 404

    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or topic.name).strip()
    description = payload.get("description", topic.description)
    parent_id = payload.get("parentTopicID", topic.parent_topic_id)

    # Prüfe, ob das Parent-Topic existiert (falls angegeben)
    if parent_id:
        parent = Topic.query.get(parent_id)
        if not parent:
            return jsonify({"error": "parentTopicID not found"}), 422
    
    topic.name = name
    topic.description = description
    topic.parent_topic_id = parent_id
    db.session.commit()
    return topic.to_dict()



# Löscht ein Topic, wenn keine abhängigen Skills oder Subtopics existieren
@app.route('/topics/<id>', methods=['DELETE'])
def delete_topic(id):
    """
    Löscht ein Lern-Topic anhand seiner ID.
    Verhindert das Löschen, wenn abhängige Skills oder Subtopics existieren.
    Gibt 204 No Content zurück, wenn erfolgreich gelöscht.
    """
    topic = Topic.query.get(id)

    if not topic:
        return jsonify({"error": "Topic not found"}), 404

    # Prüfe, ob abhängige Skills oder Subtopics existieren
    has_skills = db.session.query(exists().where(Skill.topic_id == id)).scalar()
    has_topics = db.session.query(exists().where(Topic.parent_topic_id == id)).scalar()

    if has_skills:
        return jsonify({"error": "The topic has dependent skills, cannot delete the topic"}), 409

    if has_topics:
        return jsonify({"error": "The topic has dependent topics, cannot delete the topic"}), 409

    db.session.delete(topic)
    db.session.commit()
    return "", 204



# =====================
#   SKILL ENDPUNKTE
# =====================


# Gibt alle Skills als Liste zurück
@app.route('/skills', methods=['GET'])
def get_skills():
    """
    Ruft alle verfügbaren Lern-Skills aus der Datenbank ab und gibt sie als Liste zurück.
    """
    rows = Skill.query.order_by(Skill.name.asc()).all()
    data = [skill.to_dict() for skill in rows]
    return jsonify(data)


# Gibt einen einzelnen Skill anhand der ID zurück
@app.route('/skills/<id>', methods=['GET'])
def get_skill_by_id(id):
    """
    Ruft einen einzelnen Lern-Skill anhand seiner ID ab.
    Gibt 404 zurück, wenn der Skill nicht existiert.
    """
    skill = Skill.query.get(id)
    if not skill:
        return jsonify({"error": "Skill not found"}), 404
    return skill.to_dict()


# Legt einen neuen Skill an
@app.route('/skills', methods=['POST'])
def create_skill():
    """
    Erstellt einen neuen Lern-Skill.
    Erwartet 'name', 'topicID' und 'difficulty' im JSON-Body.
    Prüft, ob das zugehörige Topic existiert.
    """
    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or "").strip()
    topic_id = payload.get("topicID")
    difficulty = (payload.get("difficulty") or "unknown").strip()

    if not name:
        return jsonify({"error": "Field 'name' is required."}), 422
    if not topic_id:
        return jsonify({"error": "Field 'topicID' is required."}), 422

    # Prüfe, ob das Topic existiert
    topic = Topic.query.get(topic_id)
    if not topic:
        return jsonify({"error": "topicID not found"}), 422

    skill = Skill(name=name, topic_id=topic_id, difficulty=difficulty)
    db.session.add(skill)
    db.session.commit()
    return skill.to_dict(), 201


# Aktualisiert einen bestehenden Skill anhand der ID
@app.route('/skills/<id>', methods=['PUT'])
def update_skill(id):
    """
    Aktualisiert einen bestehenden Lern-Skill anhand seiner ID.
    Erwartet 'name', 'topicID' und 'difficulty' im JSON-Body.
    Prüft, ob das zugehörige Topic existiert.
    """
    skill = Skill.query.get(id)
    if not skill:
        return jsonify({"error": "Skill not found"}), 404

    payload = request.get_json(silent=True) or {}
    name = (payload.get("name") or skill.name).strip()
    topic_id = payload.get("topicID", skill.topic_id)
    difficulty = (payload.get("difficulty") or skill.difficulty).strip()

    # Prüfe, ob das Topic existiert
    topic = Topic.query.get(topic_id)
    if not topic:
        return jsonify({"error": "topicID not found"}), 422

    skill.name = name
    skill.topic_id = topic_id
    skill.difficulty = difficulty
    db.session.commit()
    return skill.to_dict()


# Löscht einen Skill anhand der ID
@app.route('/skills/<id>', methods=['DELETE'])
def delete_skill(id):
    """
    Löscht einen Lern-Skill anhand seiner ID.
    Gibt 204 No Content zurück, wenn erfolgreich gelöscht.
    """
    skill = Skill.query.get(id)
    if not skill:
        return jsonify({"error": "Skill not found"}), 404
    db.session.delete(skill)
    db.session.commit()
    return '', 204

if __name__ == '__main__':
    # Startet den Flask-Entwicklungsserver.
    # debug=True ermöglicht automatische Neuladung bei Codeänderungen und detailliertere Fehlermeldungen.
    # port=5000 legt den Port fest, auf dem der Server läuft (http://127.0.0.1:5000/).
    app.run(debug=True, port=5000)
