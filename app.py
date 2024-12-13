from flask import Flask, request, jsonify
import psycopg2
from kafka import KafkaProducer
import json

app = Flask(__name__)

# Kafka producer setup
producer = KafkaProducer(
    bootstrap_servers='kafka:9093',
    value_serializer=lambda v: json.dumps(v).encode('utf-8')
)

# Database connection
def get_db_connection():
    conn = psycopg2.connect(
        dbname='messaging', user='user', password='password', host='localhost'
    )
    return conn


# Create tables if they don't exist
def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL
    );
    CREATE TABLE IF NOT EXISTS messages (
        id SERIAL PRIMARY KEY,
        sender_id INT REFERENCES users(id),
        receiver_id INT REFERENCES users(id),
        message TEXT,
        timestamp TIMESTAMPTZ DEFAULT NOW()
    );
    ''')
    conn.commit()
    cursor.close()
    conn.close()

@app.route('/register', methods=['POST'])
def register_user():
    username = request.json.get('username')
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('INSERT INTO users (username) VALUES (%s) RETURNING id;', (username,))
        user_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        return jsonify({"id": user_id, "username": username}), 201
    except Exception as e:
        conn.rollback()
        cursor.close()
        return jsonify({"error": "User already exists"}), 400
    finally:
        conn.close()

@app.route('/message', methods=['POST'])
def send_message():
    sender_id = request.json.get('sender_id')
    receiver_id = request.json.get('receiver_id')
    message = request.json.get('message')

    # Save message to database
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO messages (sender_id, receiver_id, message) VALUES (%s, %s, %s) RETURNING id;', 
                   (sender_id, receiver_id, message))
    message_id = cursor.fetchone()[0]
    conn.commit()

    # Push to Kafka topic
    producer.send('message_topic', {'sender_id': sender_id, 'receiver_id': receiver_id, 'message': message, 'message_id': message_id})

    cursor.close()
    conn.close()
    return jsonify({"message_id": message_id}), 201

if __name__ == '__main__':
    create_tables()
    app.run(debug=True, host="0.0.0.0", port=5000)