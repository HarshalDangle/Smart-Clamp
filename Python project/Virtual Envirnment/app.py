# app.py
from flask import Flask, request, jsonify, redirect, url_for, send_from_directory
import sqlite3
import uuid # For generating unique IDs
import os   # For environment variables or file paths
import datetime # For better timestamp handling

# Initialize Flask app.
# static_folder='.' tells Flask to look for static files (like police_app.html) in the current directory.
# static_url_path='' makes these files accessible directly at the root (e.g., /police_app.html).
app = Flask(__name__, static_folder='.', static_url_path='')

DATABASE = 'smart_clamp.db' # Using SQLite for simplicity initially

# Add this new route to serve police_app.html at the root URL
@app.route('/')
def serve_police_app():
    return send_from_directory(app.static_folder, 'police_app.html')

# ... (rest of your API endpoints: apply_clamp, payment_page, process_payment, clamp_status_update, police_dashboard) ...

if __name__ == '__main__':
    if not os.path.exists(DATABASE):
        print("Initializing database...")
        init_db()
    app.run(debug=True)

# --- Database Initialization ---
def init_db():
    """
    Initializes the SQLite database, creating 'clamps' and 'violations' tables
    if they do not already exist.
    """
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        # Create clamps table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clamps (
                clamp_id TEXT PRIMARY KEY,
                status TEXT DEFAULT 'available', -- e.g., 'available', 'applied', 'unlocked', 'tampered', 'low_battery'
                location_lat REAL,
                location_lon REAL,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        # Create violations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS violations (
                violation_id TEXT PRIMARY KEY,
                clamp_id TEXT,
                vehicle_number TEXT NOT NULL,
                owner_phone TEXT NOT NULL,
                fine_amount REAL NOT NULL,
                violation_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                payment_status TEXT DEFAULT 'pending', -- e.g., 'pending', 'paid', 'failed'
                payment_link TEXT,
                unlocked_time TIMESTAMP,
                FOREIGN KEY (clamp_id) REFERENCES clamps (clamp_id)
            )
        ''')
        conn.commit()

# --- Routes and API Endpoints ---

# Route to serve the main police application HTML file
@app.route('/')
def serve_police_app():
    """
    Serves the police_app.html file from the root URL.
    This resolves the 'Failed to fetch' error by serving the HTML from the same origin as the API.
    """
    return send_from_directory(app.static_folder, 'police_app.html')

# 1. Endpoint for Police to "Apply Clamp"
@app.route('/api/apply_clamp', methods=['POST'])
def apply_clamp():
    """
    Handles the request to apply a smart clamp to a vehicle.
    Records the violation details in the database and generates a payment link.
    """
    data = request.json
    clamp_id = data.get('clamp_id')
    vehicle_number = data.get('vehicle_number')
    owner_phone = data.get('owner_phone')
    fine_amount = data.get('fine_amount')
    location_lat = data.get('location_lat')
    location_lon = data.get('location_lon')

    # Basic input validation
    if not all([clamp_id, vehicle_number, owner_phone, fine_amount is not None]):
        return jsonify({"message": "Missing required fields (clamp_id, vehicle_number, owner_phone, fine_amount)"}), 400
    
    if not isinstance(fine_amount, (int, float)) or fine_amount <= 0:
        return jsonify({"message": "Fine amount must be a positive number"}), 400

    violation_id = str(uuid.uuid4())
    # Construct the payment link. In a real deployed application, this would be your domain.
    payment_link = f"http://localhost:5000/pay/{violation_id}"

    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            
            # Insert or update clamp status to 'applied'
            # If clamp_id already exists, its status will be updated.
            # If not, a new clamp record will be created.
            cursor.execute("INSERT OR REPLACE INTO clamps (clamp_id, status, location_lat, location_lon, last_seen) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)",
                           (clamp_id, 'applied', location_lat, location_lon))
            
            # Record the new violation
            cursor.execute("INSERT INTO violations (violation_id, clamp_id, vehicle_number, owner_phone, fine_amount, payment_link) VALUES (?, ?, ?, ?, ?, ?)",
                           (violation_id, clamp_id, vehicle_number, owner_phone, fine_amount, payment_link))
            conn.commit()

        # TODO: In a real system, integrate with an actual SMS gateway (e.g., Twilio, Fast2SMS)
        # to send the payment_link to the owner_phone.
        print(f"SMS simulation: Sent to {owner_phone} with link: {payment_link}")

        return jsonify({
            "message": "Clamp applied and violation recorded successfully.",
            "violation_id": violation_id,
            "payment_link": payment_link
        }), 201
    except sqlite3.Error as e:
        # Catch specific database errors
        return jsonify({"message": f"Database error occurred: {e}"}), 500
    except Exception as e:
        # Catch any other unexpected errors
        return jsonify({"message": f"An unexpected error occurred: {e}"}), 500

# 2. Endpoint for Car Owner Payment Page
@app.route('/pay/<violation_id>')
def payment_page(violation_id):
    """
    Renders the payment page for the car owner.
    Displays violation details and a button to simulate payment.
    """
    with sqlite3.connect(DATABASE) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT vehicle_number, fine_amount, payment_status FROM violations WHERE violation_id = ?", (violation_id,))
        violation = cursor.fetchone()

    if not violation:
        return "<h1>Violation Not Found</h1><p>The violation ID provided is invalid or the record does not exist.</p>", 404

    vehicle_number, fine_amount, payment_status = violation

    # Check if payment is already made
    if payment_status == 'paid':
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Fine Paid</title>
            <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
            <style>
                body {{ font-family: 'Inter', sans-serif; text-align: center; margin-top: 50px; background-color: #f0f2f5; color: #333; }}
                .container {{
                    width: 90%; max-width: 500px; margin: auto; padding: 30px;
                    background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                    border: 1px solid #e0e0e0;
                }}
                h1 {{ color: #28a745; margin-bottom: 15px; }}
                p {{ font-size: 1.1em; line-height: 1.6; }}
                .message-box {{
                    margin-top: 20px; padding: 15px; border-radius: 8px;
                    font-weight: bold;
                }}
                .success {{ background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>Fine Already Paid!</h1>
                <p>Vehicle Number: <strong>{vehicle_number}</strong></p>
                <p>Fine Amount: <strong>₹{fine_amount:.2f}</strong></p>
                <div class="message-box success">
                    Thank you! Your fine has already been successfully paid.
                </div>
            </div>
        </body>
        </html>
        """, 200

    # Render payment page if fine is pending
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Pay Parking Fine</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
        <style>
            body {{ font-family: 'Inter', sans-serif; text-align: center; margin-top: 50px; background-color: #f0f2f5; color: #333; }}
            .container {{
                width: 90%; max-width: 500px; margin: auto; padding: 30px;
                background-color: #ffffff; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1);
                border: 1px solid #e0e0e0;
            }}
            h1 {{ color: #007bff; margin-bottom: 15px; }}
            p {{ font-size: 1.1em; line-height: 1.6; }}
            button {{
                padding: 12px 25px; background-color: #28a745; color: white;
                border: none; border-radius: 8px; cursor: pointer;
                font-size: 1.1em; font-weight: 600;
                transition: background-color 0.3s ease, transform 0.2s ease;
                box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            }}
            button:hover {{ background-color: #218838; transform: translateY(-2px); }}
            button:active {{ transform: translateY(0); box-shadow: 0 2px 4px rgba(0,0,0,0.2); }}
            .message-box {{
                margin-top: 20px; padding: 15px; border-radius: 8px;
                font-weight: bold;
            }}
            .success {{ background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }}
            .error {{ background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }}
            .info {{ background-color: #cfe2ff; color: #055160; border: 1px solid #b6d4fe; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Parking Fine for Vehicle: {vehicle_number}</h1>
            <p>Fine Amount: <strong>₹{fine_amount:.2f}</strong></p>
            <p>Violation ID: <code>{violation_id}</code></p>
            <button onclick="simulatePayment('{violation_id}')">Simulate Pay Now</button>
            <div id="message" class="message-box info">Please click 'Simulate Pay Now' to proceed.</div>
        </div>

        <script>
            async function simulatePayment(violationId) {{
                const messageDiv = document.getElementById('message');
                messageDiv.className = 'message-box info';
                messageDiv.innerText = 'Processing payment... Please wait.';

                try {{
                    const response = await fetch(`/api/process_payment/${violationId}`, {{ method: 'POST' }});
                    const data = await response.json();
                    
                    if (response.ok) {{
                        messageDiv.className = 'message-box success';
                        messageDiv.innerText = data.message;
                        // Optionally, disable button or redirect after success
                        document.querySelector('button').disabled = true;
                        setTimeout(() => {{
                            window.location.reload(); // Reload to show "Fine Already Paid" state
                        }}, 2000); // Reload after 2 seconds
                    }} else {{
                        messageDiv.className = 'message-box error';
                        messageDiv.innerText = `Error: ${data.message || 'Payment failed.'}`;
                    }}
                }} catch (error) {{
                    messageDiv.className = 'message-box error';
                    messageDiv.innerText = `Network error: ${error.message}. Please try again.`;
                }}
            }}
        </script>
    </body>
    </html>
    """

# 3. Endpoint for Server to "Process Payment" (Simulated)
@app.route('/api/process_payment/<violation_id>', methods=['POST'])
def process_payment(violation_id):
    """
    Simulates the payment processing and triggers the clamp unlock.
    In a real system, this would be called by a payment gateway's webhook after successful transaction.
    """
    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT clamp_id, payment_status FROM violations WHERE violation_id = ?", (violation_id,))
            violation_data = cursor.fetchone()

            if not violation_data:
                return jsonify({"message": "Violation not found."}), 404

            clamp_id, payment_status = violation_data

            if payment_status == 'paid':
                return jsonify({"message": "Fine already paid. Clamp should be unlocked."}), 409 # Conflict

            # Update violation status to 'paid' and record unlock time
            cursor.execute("UPDATE violations SET payment_status = 'paid', unlocked_time = CURRENT_TIMESTAMP WHERE violation_id = ?", (violation_id,))
            # Update clamp status to 'unlocked'
            cursor.execute("UPDATE clamps SET status = 'unlocked', last_seen = CURRENT_TIMESTAMP WHERE clamp_id = ?", (clamp_id,))
            conn.commit()

        # TODO: This is the critical integration point for the E&TC part.
        # Here, you would send the actual UNLOCK command to the physical clamp (e.g., via MQTT, HTTP to an IoT platform, or direct cellular message).
        print(f"DEBUG: UNLOCK command dispatched to physical clamp: {clamp_id} for violation: {violation_id}")

        return jsonify({"message": "Payment successful. Clamp has been commanded to unlock."}), 200
    except sqlite3.Error as e:
        return jsonify({"message": f"Database error during payment processing: {e}"}), 500
    except Exception as e:
        return jsonify({"message": f"An unexpected error occurred during payment processing: {e}"}), 500

# 4. Endpoint for Clamp to Update Status (e.g., battery, tamper)
@app.route('/api/clamp_status_update', methods=['POST'])
def clamp_status_update():
    """
    Allows a physical clamp to send status updates (e.g., battery level, tamper alerts).
    """
    data = request.json
    clamp_id = data.get('clamp_id')
    status = data.get('status') # e.g., 'tampered', 'low_battery', 'locked', 'unlocked'
    location_lat = data.get('location_lat')
    location_lon = data.get('location_lon')

    if not all([clamp_id, status]):
        return jsonify({"message": "Missing required fields (clamp_id, status)"}), 400

    try:
        with sqlite3.connect(DATABASE) as conn:
            cursor = conn.cursor()
            # Update existing clamp's status and last_seen.
            # Only update location if provided.
            update_query = "UPDATE clamps SET status = ?, last_seen = CURRENT_TIMESTAMP"
            params = [status]
            if location_lat is not None and location_lon is not None:
                update_query += ", location_lat = ?, location_lon = ?"
                params.extend([location_lat, location_lon])
            update_query += " WHERE clamp_id = ?"
            params.append(clamp_id)

            cursor.execute(update_query, tuple(params))
            
            # If the clamp doesn't exist, create a new entry for it
            if cursor.rowcount == 0:
                cursor.execute("INSERT INTO clamps (clamp_id, status, location_lat, location_lon, last_seen) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)",
                               (clamp_id, status, location_lat, location_lon))
            
            conn.commit()
        return jsonify({"message": f"Clamp {clamp_id} status updated to '{status}'."}), 200
    except sqlite3.Error as e:
        return jsonify({"message": f"Database error during status update: {e}"}), 500
    except Exception as e:
        return jsonify({"message": f"An unexpected error occurred during status update: {e}"}), 500

# 5. Police Dashboard to view all active clamps and violations
@app.route('/police_dashboard')
def police_dashboard():
    """
    Provides a simple web dashboard for police to view all active clamps and violations.
    """
    clamps_data = []
    violations_data = []

    with sqlite3.connect(DATABASE) as conn:
        conn.row_factory = sqlite3.Row # Allows accessing columns by name
        cursor = conn.cursor()

        # Fetch all clamps
        cursor.execute("SELECT clamp_id, status, location_lat, location_lon, last_seen FROM clamps ORDER BY last_seen DESC")
        clamps_data = [dict(row) for row in cursor.fetchall()]

        # Fetch all violations
        cursor.execute("SELECT violation_id, clamp_id, vehicle_number, owner_phone, fine_amount, violation_time, payment_status, unlocked_time FROM violations ORDER BY violation_time DESC")
        violations_data = [dict(row) for row in cursor.fetchall()]

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Police Dashboard</title>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
        <style>
            body {{ font-family: 'Inter', sans-serif; margin: 20px; background-color: #f0f2f5; color: #333; }}
            .container {{ background-color: #fff; padding: 30px; border-radius: 12px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); margin-bottom: 30px; }}
            h1, h2 {{ text-align: center; color: #007bff; margin-bottom: 25px; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
            th, td {{ border: 1px solid #e0e0e0; padding: 12px; text-align: left; }}
            th {{ background-color: #f2f2f2; font-weight: 600; color: #555; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
            .status-applied {{ color: #dc3545; font-weight: bold; }}
            .status-unlocked {{ color: #28a745; font-weight: bold; }}
            .status-pending {{ color: #ffc107; font-weight: bold; }}
            .status-paid {{ color: #28a745; font-weight: bold; }}
            .no-data {{ text-align: center; color: #666; padding: 20px; }}
            .back-button {{
                display: block; width: fit-content; margin: 20px auto;
                padding: 10px 20px; background-color: #6c757d; color: white;
                border: none; border-radius: 8px; text-decoration: none;
                font-size: 1em; transition: background-color 0.3s ease;
            }}
            .back-button:hover {{ background-color: #5a6268; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Police Dashboard</h1>

            <h2>Clamps Status</h2>
            {
                "<table><thead><tr><th>Clamp ID</th><th>Status</th><th>Latitude</th><th>Longitude</th><th>Last Seen</th></tr></thead><tbody>" +
                "".join([
                    f"""
                    <tr>
                        <td>{clamp['clamp_id']}</td>
                        <td class="{ 'status-applied' if clamp['status'] == 'applied' else ('status-unlocked' if clamp['status'] == 'unlocked' else '') }">
                            {clamp['status']}
                        </td>
                        <td>{clamp['location_lat'] if clamp['location_lat'] is not None else 'N/A'}</td>
                        <td>{clamp['location_lon'] if clamp['location_lon'] is not None else 'N/A'}</td>
                        <td>{clamp['last_seen']}</td>
                    </tr>
                    """ for clamp in clamps_data
                ]) +
                "</tbody></table>" if clamps_data else "<p class='no-data'>No clamp data available.</p>"
            }

            <h2>Violation Records</h2>
            {
                "<table><thead><tr><th>Violation ID</th><th>Clamp ID</th><th>Vehicle No.</th><th>Owner Phone</th><th>Fine Amt.</th><th>Violation Time</th><th>Payment Status</th><th>Unlocked Time</th></tr></thead><tbody>" +
                "".join([
                    f"""
                    <tr>
                        <td>{violation['violation_id']}</td>
                        <td>{violation['clamp_id']}</td>
                        <td>{violation['vehicle_number']}</td>
                        <td>{violation['owner_phone']}</td>
                        <td>₹{violation['fine_amount']:.2f}</td>
                        <td>{violation['violation_time']}</td>
                        <td class="{ 'status-paid' if violation['payment_status'] == 'paid' else 'status-pending' }">
                            {violation['payment_status']}
                        </td>
                        <td>{violation['unlocked_time'] if violation['unlocked_time'] else 'N/A'}</td>
                    </tr>
                    """ for violation in violations_data
                ]) +
                "</tbody></table>" if violations_data else "<p class='no-data'>No violation data available.</p>"
            }
        </div>
        <a href="/" class="back-button">Back to Police Application</a>
    </body>
    </html>
    """


# --- Run the App ---
if __name__ == '__main__':
    # Initialize database only if the file does not exist
    if not os.path.exists(DATABASE):
        print("Initializing database...")
        init_db()
    
    # Run the Flask application
    # debug=True allows auto-reloading on code changes and provides a debugger
    app.run(debug=True)
