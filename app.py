import os
import pytesseract
from PIL import Image
from werkzeug.utils import secure_filename
from rapidfuzz import fuzz

SYMPTOM_TO_CATEGORY = {
    "fever": "Painkiller",
    "headache": "Painkiller",
    "body pain": "Painkiller",
    "pain": "Painkiller",
    "cold": "Antibiotic",
    "cough": "Antibiotic",
    "infection": "Antibiotic",
    "throat pain": "Antibiotic",
    "injury": "trauma",
    "wound": "trauma",
    "cut": "trauma",
    "sprain": "trauma",
}

pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
from math import radians, cos, sin, asin, sqrt
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db_connection

app = Flask(__name__)
app.secret_key = 'change-this-to-something-secret'
ADMIN_EMAIL = 'admin@medsystem.com'
ADMIN_PASSWORD = 'admin123'

@app.route('/')
def home():
    return render_template('index.html')

# ---------- USER AUTH ----------

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        try:
            conn.execute(
                'INSERT INTO users (name, email, password) VALUES (?, ?, ?)',
                (name, email, hashed_password)
            )
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except Exception:
            conn.close()
            return render_template('register.html', error='Email already registered.')

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html', error='Invalid email or password.')

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('dashboard.html', user_name=session['user_name'])

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ---------- PHARMACY AUTH ----------

@app.route('/pharmacy/register', methods=['GET', 'POST'])
def pharmacy_register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        address = request.form['address']
        contact = request.form['contact']
        latitude = request.form.get('latitude') or None
        longitude = request.form.get('longitude') or None
        hashed_password = generate_password_hash(password)

        conn = get_db_connection()
        try:
            conn.execute(
                'INSERT INTO pharmacies (name, email, password, address, contact, latitude, longitude) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (name, email, hashed_password, address, contact, latitude, longitude)
            )
            conn.commit()
            conn.close()
            return redirect(url_for('pharmacy_login'))
        except Exception:
            conn.close()
            return render_template('pharmacy_register.html', error='Email already registered.')

    return render_template('pharmacy_register.html')

@app.route('/pharmacy/login', methods=['GET', 'POST'])
def pharmacy_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        pharmacy = conn.execute('SELECT * FROM pharmacies WHERE email = ?', (email,)).fetchone()
        conn.close()

        if pharmacy and check_password_hash(pharmacy['password'], password):
            if pharmacy['is_approved'] == 0:
                return render_template('pharmacy_login.html', error='Your pharmacy account is pending admin approval. Please check back later.')
            session['pharmacy_id'] = pharmacy['id']
            session['pharmacy_name'] = pharmacy['name']
            return redirect(url_for('pharmacy_dashboard'))
        else:
            return render_template('pharmacy_login.html', error='Invalid email or password.')

    return render_template('pharmacy_login.html')

@app.route('/pharmacy/dashboard')
def pharmacy_dashboard():
    if 'pharmacy_id' not in session:
        return redirect(url_for('pharmacy_login'))

    conn = get_db_connection()
    inventory = conn.execute('''
        SELECT inventory.id AS inventory_id, medicines.name, medicines.generic_name,
               medicines.category, inventory.quantity, inventory.price, inventory.updated_at
        FROM inventory
        JOIN medicines ON inventory.medicine_id = medicines.id
        WHERE inventory.pharmacy_id = ?
    ''', (session['pharmacy_id'],)).fetchall()
    conn.close()

    return render_template('pharmacy_dashboard.html',
                            pharmacy_name=session['pharmacy_name'],
                            inventory=inventory)

@app.route('/pharmacy/logout')
def pharmacy_logout():
    session.clear()
    return redirect(url_for('pharmacy_login'))

@app.route('/pharmacy/add-medicine', methods=['GET', 'POST'])
def add_medicine():
    if 'pharmacy_id' not in session:
        return redirect(url_for('pharmacy_login'))

    if request.method == 'POST':
        medicine_name = request.form['medicine_name'].strip()
        generic_name = request.form['generic_name'].strip()
        category = request.form['category'].strip()
        quantity = request.form['quantity']
        price = request.form['price']
        pharmacy_id = session['pharmacy_id']

        conn = get_db_connection()

        # Check if medicine already exists (case-insensitive match)
        medicine = conn.execute(
            'SELECT * FROM medicines WHERE LOWER(name) = LOWER(?)', (medicine_name,)
        ).fetchone()

        if medicine:
            medicine_id = medicine['id']
        else:
            cursor = conn.execute(
                'INSERT INTO medicines (name, generic_name, category) VALUES (?, ?, ?)',
                (medicine_name, generic_name, category)
            )
            medicine_id = cursor.lastrowid

        # Check if this pharmacy already has this medicine in inventory
        existing = conn.execute(
            'SELECT * FROM inventory WHERE pharmacy_id = ? AND medicine_id = ?',
            (pharmacy_id, medicine_id)
        ).fetchone()

        if existing:
            conn.execute(
                'UPDATE inventory SET quantity = ?, price = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                (quantity, price, existing['id'])
            )
        else:
            conn.execute(
                'INSERT INTO inventory (pharmacy_id, medicine_id, quantity, price) VALUES (?, ?, ?, ?)',
                (pharmacy_id, medicine_id, quantity, price)
            )

        conn.commit()
        conn.close()
        return redirect(url_for('pharmacy_dashboard'))

    return render_template('add_medicine.html')
def calculate_distance(lat1, lon1, lat2, lon2):
    # Haversine formula: calculates distance in km between two GPS points
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371  # Earth's radius in km
    return round(c * r, 2)

@app.route('/search')
def search():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    query = request.args.get('query', '').strip()
    category = request.args.get('category', '').strip()
    symptom = request.args.get('symptom', '').strip().lower()

    if symptom and not category:
        for keyword, mapped_category in SYMPTOM_TO_CATEGORY.items():
            if keyword in symptom:
                category = mapped_category
                break
    lat = request.args.get('lat', '').strip()
    lng = request.args.get('lng', '').strip()
    results = []
    medicine_exists = True
    alternatives = []

    conn = get_db_connection()
    all_categories = conn.execute(
        'SELECT DISTINCT category FROM medicines WHERE category IS NOT NULL AND category != "" ORDER BY category'
    ).fetchall()

    if query or category:
        sql = '''
            SELECT pharmacies.id AS pharmacy_id,
                   pharmacies.name AS pharmacy_name,
                   pharmacies.address,
                   pharmacies.contact,
                   pharmacies.latitude,
                   pharmacies.longitude,
                   medicines.id AS medicine_id,
                   medicines.name AS medicine_name,
                   medicines.category,
                   inventory.quantity,
                   inventory.price
            FROM inventory
            JOIN pharmacies ON inventory.pharmacy_id = pharmacies.id
            JOIN medicines ON inventory.medicine_id = medicines.id
            WHERE inventory.quantity > 0
        '''
        params = []

        if query:
            sql += ' AND LOWER(medicines.name) LIKE LOWER(?)'
            params.append('%' + query + '%')

        if category:
            sql += ' AND LOWER(medicines.category) = LOWER(?)'
            params.append(category)

        rows = conn.execute(sql, params).fetchall()
        results = [dict(row) for row in rows]

        if lat and lng:
            user_lat, user_lng = float(lat), float(lng)
            for item in results:
                if item['latitude'] and item['longitude']:
                    item['distance'] = calculate_distance(
                        user_lat, user_lng, item['latitude'], item['longitude']
                    )
                else:
                    item['distance'] = None
            results.sort(key=lambda x: (x['distance'] is None, x['distance']))
        else:
            results.sort(key=lambda x: -x['quantity'])

        if query:
            medicine_check = conn.execute(
                'SELECT * FROM medicines WHERE LOWER(name) LIKE LOWER(?)', ('%' + query + '%',)
            ).fetchone()
            medicine_exists = medicine_check is not None

            if not results and medicine_check and medicine_check['generic_name']:
                generic = medicine_check['generic_name']
                alt_rows = conn.execute('''
                    SELECT pharmacies.name AS pharmacy_name,
                           pharmacies.address,
                           pharmacies.contact,
                           medicines.name AS medicine_name,
                           medicines.generic_name,
                           inventory.quantity,
                           inventory.price
                    FROM inventory
                    JOIN pharmacies ON inventory.pharmacy_id = pharmacies.id
                    JOIN medicines ON inventory.medicine_id = medicines.id
                    WHERE LOWER(medicines.generic_name) = LOWER(?)
                      AND LOWER(medicines.name) != LOWER(?)
                      AND inventory.quantity > 0
                    ORDER BY inventory.quantity DESC
                ''', (generic, query)).fetchall()
                alternatives = [dict(row) for row in alt_rows]

    conn.close()

    return render_template('search.html', query=query, results=results,
                            medicine_exists=medicine_exists, lat=lat,
                            alternatives=alternatives, all_categories=all_categories,
                            selected_category=category)
@app.route('/upload-prescription', methods=['GET', 'POST'])
def upload_prescription():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    extracted_text = None
    matched_medicines = []

    if request.method == 'POST':
        file = request.files['prescription']
        if file:
            filename = secure_filename(file.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            file.save(filepath)

            # Run OCR on the image
            image = Image.open(filepath)
            extracted_text = pytesseract.image_to_string(image)

            # Match extracted words against known medicines in the database
            conn = get_db_connection()
            all_medicines = conn.execute('SELECT name FROM medicines').fetchall()
            conn.close()

            extracted_lower = extracted_text.lower()

            for med in all_medicines:
                med_name_lower = med['name'].lower()

                # Exact match (substring) - fastest, most reliable
                if med_name_lower in extracted_lower:
                    matched_medicines.append(med['name'])
                    continue

                # Fuzzy match - checks if medicine name closely matches
                # any part of the extracted text, handling multi-word names and OCR typos
                similarity = fuzz.partial_ratio(med_name_lower, extracted_lower)
                if similarity >= 75:
                    matched_medicines.append(med['name'])

    return render_template('upload_prescription.html',
                            extracted_text=extracted_text,
                            matched_medicines=matched_medicines)
@app.route('/request-medicine', methods=['POST'])
def request_medicine():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    medicine_name = request.form['medicine_name']
    conn = get_db_connection()
    conn.execute(
        'INSERT INTO requests (user_id, medicine_name) VALUES (?, ?)',
        (session['user_id'], medicine_name)
    )
    conn.commit()
    conn.close()

    return f"Your request for '{medicine_name}' has been submitted. <br><a href='/search'>Back to Search</a>"
@app.route('/pharmacy/requests')
def pharmacy_requests():
    if 'pharmacy_id' not in session:
        return redirect(url_for('pharmacy_login'))

    conn = get_db_connection()
    requests_list = conn.execute('''
        SELECT requests.id, requests.medicine_name, requests.status, requests.created_at,
               users.name AS user_name
        FROM requests
        JOIN users ON requests.user_id = users.id
        ORDER BY requests.created_at DESC
    ''').fetchall()
    conn.close()

    return render_template('pharmacy_requests.html', requests=requests_list)

@app.route('/pharmacy/fulfill-request/<int:request_id>', methods=['POST'])
def fulfill_request(request_id):
    if 'pharmacy_id' not in session:
        return redirect(url_for('pharmacy_login'))

    conn = get_db_connection()
    conn.execute('UPDATE requests SET status = ? WHERE id = ?', ('fulfilled', request_id))
    conn.commit()
    conn.close()

    return redirect(url_for('pharmacy_requests'))
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        if email == ADMIN_EMAIL and password == ADMIN_PASSWORD:
            session['is_admin'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template('admin_login.html', error='Invalid admin credentials.')

    return render_template('admin_login.html')

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))

    conn = get_db_connection()
    total_users = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    total_pharmacies = conn.execute('SELECT COUNT(*) FROM pharmacies').fetchone()[0]
    total_medicines = conn.execute('SELECT COUNT(*) FROM medicines').fetchone()[0]
    total_requests = conn.execute('SELECT COUNT(*) FROM requests').fetchone()[0]
    pharmacies = conn.execute('SELECT * FROM pharmacies WHERE is_approved = 1').fetchall()
    pending_pharmacies = conn.execute('SELECT * FROM pharmacies WHERE is_approved = 0').fetchall()
    users = conn.execute('SELECT * FROM users').fetchall()
    medicines = conn.execute('SELECT * FROM medicines').fetchall()
    all_requests = conn.execute('''
        SELECT requests.medicine_name, requests.status, requests.created_at,
               users.name AS user_name
        FROM requests
        JOIN users ON requests.user_id = users.id
        ORDER BY requests.created_at DESC
    ''').fetchall()

    top_requested = conn.execute('''
        SELECT medicine_name, COUNT(*) AS request_count
        FROM requests
        GROUP BY LOWER(medicine_name)
        ORDER BY request_count DESC
        LIMIT 5
    ''').fetchall()

    low_stock = conn.execute('''
        SELECT medicines.name AS medicine_name, pharmacies.name AS pharmacy_name, inventory.quantity
        FROM inventory
        JOIN medicines ON inventory.medicine_id = medicines.id
        JOIN pharmacies ON inventory.pharmacy_id = pharmacies.id
        WHERE inventory.quantity < 10
        ORDER BY inventory.quantity ASC
    ''').fetchall()

    category_distribution = conn.execute('''
        SELECT category, COUNT(*) AS count
        FROM medicines
        WHERE category IS NOT NULL AND category != ''
        GROUP BY LOWER(category)
        ORDER BY count DESC
    ''').fetchall()

    conn.close()

    return render_template('admin_dashboard.html',
                            total_users=total_users,
                            total_pharmacies=total_pharmacies,
                            total_medicines=total_medicines,
                            total_requests=total_requests,
                            pharmacies=pharmacies,
                            pending_pharmacies=pending_pharmacies,
                            users=users,
                            medicines=medicines,
                            all_requests=all_requests,
                            top_requested=top_requested,
                            low_stock=low_stock,
                            category_distribution=category_distribution)

@app.route('/admin/logout')
def admin_logout():
    session.pop('is_admin', None)
    return redirect(url_for('admin_login'))
@app.route('/admin/delete-pharmacy/<int:pharmacy_id>', methods=['POST'])
def delete_pharmacy(pharmacy_id):
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))

    conn = get_db_connection()
    conn.execute('DELETE FROM inventory WHERE pharmacy_id = ?', (pharmacy_id,))
    conn.execute('DELETE FROM pharmacies WHERE id = ?', (pharmacy_id,))
    conn.commit()
    conn.close()

    return redirect(url_for('admin_dashboard'))

@app.route('/admin/delete-user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))

    conn = get_db_connection()
    conn.execute('DELETE FROM requests WHERE user_id = ?', (user_id,))
    conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()

    return redirect(url_for('admin_dashboard'))
@app.route('/find-pharmacy-for-all', methods=['POST'])
def find_pharmacy_for_all():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    requested_medicines = request.form.getlist('medicines')

    conn = get_db_connection()
    pharmacies = conn.execute('SELECT * FROM pharmacies').fetchall()

    full_matches = []
    partial_matches = []

    for pharmacy in pharmacies:
        stock = conn.execute('''
            SELECT medicines.name
            FROM inventory
            JOIN medicines ON inventory.medicine_id = medicines.id
            WHERE inventory.pharmacy_id = ? AND inventory.quantity > 0
        ''', (pharmacy['id'],)).fetchall()

        stocked_names = [row['name'].lower() for row in stock]
        requested_lower = [m.lower() for m in requested_medicines]

        has = [m for m in requested_medicines if m.lower() in stocked_names]
        missing = [m for m in requested_medicines if m.lower() not in stocked_names]

        if len(has) == len(requested_medicines):
            full_matches.append(dict(pharmacy))
        elif len(has) > 0:
            partial_matches.append({
                'name': pharmacy['name'],
                'address': pharmacy['address'],
                'has': has,
                'missing': missing
            })

    conn.close()

    return render_template('pharmacy_match_results.html',
                            requested_medicines=requested_medicines,
                            full_matches=full_matches,
                            partial_matches=partial_matches)
@app.route('/pharmacy/edit-medicine/<int:inventory_id>', methods=['GET', 'POST'])
def edit_medicine(inventory_id):
    if 'pharmacy_id' not in session:
        return redirect(url_for('pharmacy_login'))

    conn = get_db_connection()

    if request.method == 'POST':
        medicine_name = request.form['medicine_name'].strip()
        generic_name = request.form['generic_name'].strip()
        category = request.form['category'].strip()
        quantity = request.form['quantity']
        price = request.form['price']

        # get the medicine_id linked to this inventory row
        inv_row = conn.execute('SELECT medicine_id FROM inventory WHERE id = ? AND pharmacy_id = ?',
                                (inventory_id, session['pharmacy_id'])).fetchone()
        if inv_row:
            conn.execute('UPDATE medicines SET name = ?, generic_name = ?, category = ? WHERE id = ?',
                         (medicine_name, generic_name, category, inv_row['medicine_id']))
            conn.execute('UPDATE inventory SET quantity = ?, price = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?',
                         (quantity, price, inventory_id))
            conn.commit()

        conn.close()
        return redirect(url_for('pharmacy_dashboard'))

    item = conn.execute('''
        SELECT inventory.id AS inventory_id, medicines.name, medicines.generic_name,
               medicines.category, inventory.quantity, inventory.price
        FROM inventory
        JOIN medicines ON inventory.medicine_id = medicines.id
        WHERE inventory.id = ? AND inventory.pharmacy_id = ?
    ''', (inventory_id, session['pharmacy_id'])).fetchone()
    conn.close()

    if not item:
        return redirect(url_for('pharmacy_dashboard'))

    return render_template('edit_medicine.html', item=item)

@app.route('/pharmacy/remove-medicine/<int:inventory_id>', methods=['POST'])
def remove_medicine(inventory_id):
    if 'pharmacy_id' not in session:
        return redirect(url_for('pharmacy_login'))

    conn = get_db_connection()
    conn.execute('DELETE FROM inventory WHERE id = ? AND pharmacy_id = ?',
                 (inventory_id, session['pharmacy_id']))
    conn.commit()
    conn.close()

    return redirect(url_for('pharmacy_dashboard'))
@app.route('/reserve-medicine', methods=['POST'])
def reserve_medicine():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    pharmacy_id = request.form['pharmacy_id']
    medicine_id = request.form['medicine_id']
    quantity = request.form['quantity']

    conn = get_db_connection()
    conn.execute(
        'INSERT INTO reservations (user_id, pharmacy_id, medicine_id, quantity) VALUES (?, ?, ?, ?)',
        (session['user_id'], pharmacy_id, medicine_id, quantity)
    )
    conn.commit()

    pharmacy = conn.execute('SELECT name FROM pharmacies WHERE id = ?', (pharmacy_id,)).fetchone()
    medicine = conn.execute('SELECT name FROM medicines WHERE id = ?', (medicine_id,)).fetchone()
    conn.close()

    return render_template('reservation_success.html',
                            pharmacy_name=pharmacy['name'],
                            medicine_name=medicine['name'])
@app.route('/pharmacy/reservations')
def pharmacy_reservations():
    if 'pharmacy_id' not in session:
        return redirect(url_for('pharmacy_login'))

    conn = get_db_connection()
    reservations = conn.execute('''
        SELECT reservations.id, reservations.quantity, reservations.status, reservations.created_at,
               users.name AS user_name, medicines.name AS medicine_name
        FROM reservations
        JOIN users ON reservations.user_id = users.id
        JOIN medicines ON reservations.medicine_id = medicines.id
        WHERE reservations.pharmacy_id = ?
        ORDER BY reservations.created_at DESC
    ''', (session['pharmacy_id'],)).fetchall()
    conn.close()

    return render_template('pharmacy_reservations.html', reservations=reservations)

@app.route('/pharmacy/confirm-reservation/<int:reservation_id>', methods=['POST'])
def confirm_reservation(reservation_id):
    if 'pharmacy_id' not in session:
        return redirect(url_for('pharmacy_login'))

    conn = get_db_connection()
    conn.execute('UPDATE reservations SET status = ? WHERE id = ? AND pharmacy_id = ?',
                 ('confirmed', reservation_id, session['pharmacy_id']))
    conn.commit()
    conn.close()

    return redirect(url_for('pharmacy_reservations'))

@app.route('/pharmacy/reject-reservation/<int:reservation_id>', methods=['POST'])
def reject_reservation(reservation_id):
    if 'pharmacy_id' not in session:
        return redirect(url_for('pharmacy_login'))

    conn = get_db_connection()
    conn.execute('UPDATE reservations SET status = ? WHERE id = ? AND pharmacy_id = ?',
                 ('rejected', reservation_id, session['pharmacy_id']))
    conn.commit()
    conn.close()

    return redirect(url_for('pharmacy_reservations'))

@app.route('/my-reservations')
def my_reservations():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    reservations = conn.execute('''
        SELECT reservations.quantity, reservations.status, reservations.created_at,
               pharmacies.name AS pharmacy_name, medicines.name AS medicine_name
        FROM reservations
        JOIN pharmacies ON reservations.pharmacy_id = pharmacies.id
        JOIN medicines ON reservations.medicine_id = medicines.id
        WHERE reservations.user_id = ?
        ORDER BY reservations.created_at DESC
    ''', (session['user_id'],)).fetchall()
    conn.close()

    return render_template('my_reservations.html', reservations=reservations)
@app.route('/admin/approve-pharmacy/<int:pharmacy_id>', methods=['POST'])
def approve_pharmacy(pharmacy_id):
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))

    conn = get_db_connection()
    conn.execute('UPDATE pharmacies SET is_approved = 1 WHERE id = ?', (pharmacy_id,))
    conn.commit()
    conn.close()

    return redirect(url_for('admin_dashboard'))

@app.route('/admin/reject-pharmacy/<int:pharmacy_id>', methods=['POST'])
def reject_pharmacy(pharmacy_id):
    if not session.get('is_admin'):
        return redirect(url_for('admin_login'))

    conn = get_db_connection()
    conn.execute('DELETE FROM pharmacies WHERE id = ?', (pharmacy_id,))
    conn.commit()
    conn.close()

    return redirect(url_for('admin_dashboard'))
if __name__ == '__main__':
    app.run(debug=True)