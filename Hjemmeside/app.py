from flask import Flask, request, render_template, redirect, url_for, flash, jsonify, session
import sqlite3
import bcrypt
import requests

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Databaseforbindelse
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# Opret tabellen, hvis den ikke eksisterer
def create_table():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            ip_address TEXT,
            alarm_time TEXT,
            stop_time TEXT
        )
    ''')

    # Opret itadmin og personale brugere, hvis de ikke findes i databasen
    hashed_itadmin_pw = bcrypt.hashpw('1234'.encode('utf-8'), bcrypt.gensalt())
    hashed_personale_pw = bcrypt.hashpw('1234'.encode('utf-8'), bcrypt.gensalt())

    try:
        c.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)', ('itadmin', hashed_itadmin_pw, 'itadmin'))
        c.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)', ('personale', hashed_personale_pw, 'personale'))
    except sqlite3.IntegrityError:
        pass  # Hvis brugerne allerede findes, gør ingenting
    
    conn.commit()
    conn.close()

create_table()

# Root route
@app.route('/')
def index():
    return render_template('index.html')

# Registration route
@app.route('/register', methods=['POST'])
def register():
    username = request.form['username']
    password = request.form['password']
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    conn = get_db_connection()
    c = conn.cursor()

    c.execute('SELECT * FROM users WHERE username = ?', (username,))
    if c.fetchone():
        flash('Username already taken.')
        return redirect(url_for('index'))

    c.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)', (username, hashed_password, 'user'))
    conn.commit()
    conn.close()
    flash('Registration successful!')
    return redirect(url_for('index'))

# Login route
@app.route('/login', methods=['POST'])
def login():
    username = request.form['username']
    password = request.form['password']

    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = c.fetchone()
    conn.close()

    if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
        session['username'] = username
        session['role'] = user['role']
        if user['role'] == 'admin':
            return redirect(url_for('admin_home', username=username))
        elif user['role'] == 'itadmin':
            return redirect(url_for('itadmin_home', username=username))
        elif user['role'] == 'personale':
            return redirect(url_for('personale_home', username=username))
        else:
            return redirect(url_for('home', username=username))

    flash('Invalid username or password.')
    return redirect(url_for('index'))

# User deletion route (Only accessible by itadmin)
@app.route('/delete_user/<username>', methods=['POST'])
def delete_user(username):
    if 'username' not in session or session['role'] != 'itadmin':
        flash('You are not authorized to delete users.')
        return redirect(url_for('index'))

    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = c.fetchone()

    if user:
        c.execute('DELETE FROM users WHERE username = ?', (username,))
        conn.commit()
        flash(f'User {username} deleted successfully.')
    else:
        flash(f'User {username} not found.')

    conn.close()
    return redirect(url_for('itadmin_home', username=session['username']))

# Home route for normal users
@app.route('/home/<username>', methods=['GET', 'POST'])
def home(username):
    conn = get_db_connection()
    c = conn.cursor()

    if request.method == 'POST':
        ip_address = request.form['ip_address']
        alarm_time = request.form['alarm_time']

        c.execute('UPDATE users SET ip_address = ?, alarm_time = ? WHERE username = ?',
                  (ip_address, alarm_time, username))
        conn.commit()

        try:
            response = requests.get(f'http://{ip_address}:8080/?status=forbundet&alarm_time={alarm_time}&username={username}')
            if response.status_code == 200:
                flash('Connection successful.')
            else:
                flash('Failed to connect to ESP32.')
        except requests.exceptions.RequestException as e:
            flash(f'Error: {e}')

    c.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = c.fetchone()
    conn.close()

    if user:
        return render_template('home.html', user=user)
    flash('User not found.')
    return redirect(url_for('index'))

# Admin home route
@app.route('/admin_home/<username>', methods=['GET'])
def admin_home(username):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username != ?', (username,))
    users = c.fetchall()
    conn.close()
    return render_template('admin_home.html', username=username, users=users)

# IT Admin home route
@app.route('/itadmin_home/<username>', methods=['GET'])
def itadmin_home(username):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username != ?', (username,))
    users = c.fetchall()
    conn.close()
    return render_template('itadmin_home.html', username=username, users=users)

# Personale home route
@app.route('/personale_home/<username>', methods=['GET', 'POST'])
def personale_home(username):
    conn = get_db_connection()
    c = conn.cursor()
    
    # Hent alle brugere
    c.execute('SELECT username, alarm_time, stop_time FROM users')
    users = c.fetchall()
    conn.close()

    return render_template('personale_home.html', users=users)

# Update stop time route
@app.route('/update_stop_time', methods=['POST'])
def update_stop_time():
    data = request.json
    if not data or 'username' not in data or 'stop_time' not in data:
        return jsonify({'error': 'Invalid data'}), 400

    username = data['username']
    stop_time = data['stop_time']

    conn = get_db_connection()
    c = conn.cursor()
    c.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = c.fetchone()
    if not user:
        return jsonify({'error': f'User {username} not found in database'}), 404

    c.execute('UPDATE users SET stop_time = ? WHERE username = ?', (stop_time, username))
    conn.commit()
    conn.close()

    return jsonify({'message': 'Stop time updated successfully'}), 200

if __name__ == '__main__':
    app.run(debug=True, host='192.168.0.226', port=5000)
