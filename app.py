from flask import Flask, request, jsonify, render_template, session, redirect
import csv
import os
import hashlib # For creating unique image fingerprints
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import send_from_directory
import smtplib
import random
from email.mime.text import MIMEText

# Global dictionary to store temporary OTPs (use a database in production)
otp_store = {} 

# Your Email Config (Use App Password for Gmail)
SENDER_EMAIL = "241fd01114@gmail.com"
SENDER_PASSWORD = "gydnvuyxgkticjvw" # Get this from Google Account Security


app = Flask(__name__)
app.secret_key = "expense_secret_key"

UPLOAD_FOLDER = "uploads"
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf"}

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

def allowed_file(filename):
    return "." in filename and \
           filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# FILE SETUP

EXPENSE_FILE = "expenses.csv"
EMPLOYEE_FILE = "employees.csv"

# Create files if not exist
if not os.path.exists(EXPENSE_FILE):
    with open(EXPENSE_FILE, "w", newline="") as f:
        pass

if not os.path.exists(EMPLOYEE_FILE):
    with open(EMPLOYEE_FILE, "w", newline="") as f:
        pass

COMPANY_CODE = "011718"

# HOME

@app.route("/")
def home():
    return render_template("login.html")

# EMPLOYEE PORTAL

@app.route("/employee_portal")
def employee_portal():
    return render_template("employee_portal.html")

@app.route("/employee")
def employee_dashboard():

    if not session.get("employee_logged_in"):
        return redirect("/employee_login")

    return render_template(
        "employee.html",
        emp_name=session.get("employee_name"),
        emp_id=session.get("employee_id")
    )

# MANAGER DASHBOARD

@app.route("/manager")
def manager_dashboard():
    if not session.get("manager_logged_in"):
        return redirect("/manager_login")
    return render_template("manager.html")

# EMPLOYEE REGISTRATION

@app.route("/employee_register", methods=["GET", "POST"])
def employee_register():
    if request.method == "POST":
        name = request.form.get("name")
        password = request.form.get("password")
        email = request.form.get("email") # ADD THIS: Get email from form
        code = request.form.get("code")

        if code != COMPANY_CODE:
            return render_template("employee_register.html", error="Invalid Company Code")

        # Check duplicate username OR email
        with open(EMPLOYEE_FILE, "r") as f:
            reader = csv.reader(f)
            for row in reader:
                if row:
                    if row[0] == name:
                        return render_template("employee_register.html", error="Username already exists")
                    if len(row) > 5 and row[5] == email:
                        return render_template("employee_register.html", error="Email already registered") # Requirement 1
                    
        # Save employee with email at the end (Index 5)
        with open(EMPLOYEE_FILE, "a", newline="") as f:
            writer = csv.writer(f)
            date = datetime.now().strftime("%d-%m-%Y")
            # Row structure: [Name, Password, Status, Date, Emp_ID, Email]
            writer.writerow([name, password, "Pending", date, "", email])

        return render_template("employee_register.html", success="Registration Successfully !")

    return render_template("employee_register.html")


# EMPLOYEE LOGIN

@app.route("/employee_login", methods=["GET", "POST"])
def employee_login():
    if request.method == "POST":
        login_input = request.form.get("name") # This field now accepts Name or Email
        password = request.form.get("password")

        with open(EMPLOYEE_FILE, "r") as f:
            reader = csv.reader(f)
            for row in reader:
                if row and len(row) > 5:
                    # Check if input matches Name (row[0]) OR Email (row[5])
                    if (row[0] == login_input or row[5] == login_input) and \
                       row[1] == password and row[2] == "Approved":

                        session["employee_logged_in"] = True
                        session["employee_name"] = row[0]
                        session["employee_id"] = row[4]
                        session["employee_email"] = row[5] # Store in session
                        return redirect("/employee")

        return render_template("employee_login.html", error="Invalid credentials or not approved")
    return render_template("employee_login.html")

@app.route("/recheck_expense", methods=["POST"])
def recheck_expense():
    if not session.get("employee_logged_in"):
        return jsonify({"error": "Unauthorized"}), 403

    expense_id = int(request.json.get("id"))

    rows = []
    with open(EXPENSE_FILE, "r") as f:
        rows = list(csv.reader(f))

    if 0 <= expense_id < len(rows):

        # Reset to pending
        rows[expense_id][6] = "Pending"
        rows[expense_id][7] = ""
        rows[expense_id][8] = ""

        with open(EXPENSE_FILE, "w", newline="") as f:
            csv.writer(f).writerows(rows)

        return jsonify({"success": True})

    return jsonify({"success": False})

@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        email = request.form.get("email").strip().lower()
        
        # 1. Validate email and fetch the Employee ID (EM-CODE)
        user_found = False
        emp_code = ""
        with open(EMPLOYEE_FILE, "r") as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) > 5 and row[5].strip().lower() == email:
                    user_found = True
                    emp_code = row[4] # Capture the EM-CODE
                    break
        
        if not user_found:
            return render_template("forgot_password.html", error="Email not registered.")

        # 2. Generate OTP
        otp = str(random.randint(100000, 999999))
        otp_store[email] = otp 

        # 3. Send OTP with custom "From" Name and EM-CODE
        try:
            # This makes the "Sender" show as "ExpenseApp System" instead of just your email
            msg = MIMEText(f"Hello {emp_code},\n\nYour OTP for Expense App password reset is: {otp}")
            msg["Subject"] = f"Password Reset for {emp_code}"
            msg["From"] = f"ExpenseApp System <{SENDER_EMAIL}>" # Custom Sender Name
            msg["To"] = email

            server = smtplib.SMTP("smtp.gmail.com", 587, timeout=15)
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)
            server.quit()
            
            session["reset_email"] = email
            return redirect("/verify_otp")
        except Exception as e:
            print(f"SMTP Error: {str(e)}")
            return render_template("forgot_password.html", error="Could not send email.")

    return render_template("forgot_password.html")

@app.route("/verify_otp", methods=["GET", "POST"])
def verify_otp():
    email = session.get("reset_email")
    if request.method == "POST":
        user_otp = request.form.get("otp")
        
        if otp_store.get(email) == user_otp: # Requirement 6
            return render_template("reset_password.html") # Open new password page
        else:
            return render_template("verify_otp.html", error="Invalid OTP.")

    return render_template("verify_otp.html")

@app.route("/reset_password", methods=["POST"])
def reset_password_action():
    email = session.get("reset_email")
    if not email:
        return redirect("/forgot_password")

    new_password = request.form.get("password")
    confirm_password = request.form.get("confirm_password")

    if new_password != confirm_password:
        return render_template("reset_password.html", error="Passwords do not match.")

    # 1. Load all employees into memory
    rows = []
    updated = False
    
    if not os.path.exists(EMPLOYEE_FILE):
        return render_template("reset_password.html", error="Database error.")

    with open(EMPLOYEE_FILE, "r") as f:
        rows = list(csv.reader(f))

    # 2. Loop through and find the specific employee by email
    for row in rows:
        if len(row) > 5:
            # Match exactly against the stored email (Index 5)
            if row[5].strip().lower() == email.strip().lower():
                row[1] = new_password # Update the password column
                updated = True
                # Keep searching just in case, but usually we could 'break' here

    # 3. Write the entire updated list back to the CSV
    if updated:
        with open(EMPLOYEE_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(rows)
        
        # Clear the session so the OTP cannot be used again
        otp_store.pop(email, None) 
        session.pop("reset_email", None)
        
        return redirect("/employee_login?success=Password Reset Successfully!")
    else:
        return render_template("reset_password.html", error="User not found in database.")

@app.route("/dashboard_partial")
def dashboard_partial():
    return render_template("dashboard_partial.html")

@app.route("/home_partial")
def home_partial():
    # Add the 'partials/' prefix so Flask can find the file
    return render_template("partials/home_partial.html")

# MANAGER LOGIN

@app.route("/manager_login", methods=["GET", "POST"])
def manager_login():

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username == "manager" and password == "1234":
            session["manager_logged_in"] = True
            return redirect("/manager")

        return render_template("manager_login.html",
                               error="Invalid Credentials")

    return render_template("manager_login.html")

# MANAGE EMPLOYEES

@app.route("/manage_employees")
def manage_employees():

    if not session.get("manager_logged_in"):
        return redirect("/manager_login")

    employees = []

    with open(EMPLOYEE_FILE, "r") as f:
        reader = csv.reader(f)
        for index, row in enumerate(reader):
            if row:
                name = row[0]
                status = row[2] if len(row) > 2 else "Pending"
                date = row[3] if len(row) > 3 else "01-01-2000"

                # Convert date string to datetime for sorting
                date_obj = datetime.strptime(date, "%d-%m-%Y")

                employees.append({
                    "id": index,
                    "name": name,
                    "status": status,
                    "date": date,
                    "date_obj": date_obj
                })

    # Sort logic:
    # Approved first, Pending next, Rejected last
    # Inside each group → newest first

    employees.sort(
        key=lambda x: (
            0 if x["status"] == "Approved" else
            1 if x["status"] == "Pending" else
            2,
            -x["date_obj"].timestamp()
        )
    )

    return render_template("manage_employees.html",
                           employees=employees)


@app.route("/employee_stats")
def employee_stats():

    if not session.get("manager_logged_in"):
        return jsonify({"error": "Unauthorized"}), 403

    total = 0
    pending = 0

    with open(EMPLOYEE_FILE, "r") as f:
        reader = csv.reader(f)
        for row in reader:
            if row:
                total += 1
                if row[2] == "Pending":
                    pending += 1

    return jsonify({
        "total": total,
        "pending": pending
    })

@app.route("/update_employee", methods=["POST"])
def update_employee():

    if not session.get("manager_logged_in"):
        return jsonify({"error": "Unauthorized"}), 403

    emp_id = int(request.form.get("id"))
    action = request.form.get("action")

    rows = []

    with open(EMPLOYEE_FILE, "r") as f:
        rows = list(csv.reader(f))

    if 0 <= emp_id < len(rows):

        if action == "approve":

            rows[emp_id][2] = "Approved"

            # Count already approved employees
            approved_count = 0
            for r in rows:
                if len(r) >= 5 and r[2] == "Approved" and r[4]:
                    approved_count += 1

            new_emp_id = f"EM{approved_count+1:02d}"

            # If employee_id column doesn't exist, add it
            if len(rows[emp_id]) < 5:
                rows[emp_id].append(new_emp_id)
            else:
                rows[emp_id][4] = new_emp_id

        elif action == "reject":
            rows[emp_id][2] = "Rejected"

    with open(EMPLOYEE_FILE, "w", newline="") as f:
        csv.writer(f).writerows(rows)

    return jsonify({"success": True})

# Upload File

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

# EXPENSE SYSTEM

@app.route("/add_expense", methods=["POST"])
def add_expense():
    if not session.get("employee_logged_in"):
        return jsonify({"success": False, "error": "Unauthorized"}), 403

    # Ensure uploads folder exists
    if not os.path.exists(app.config["UPLOAD_FOLDER"]):
        os.makedirs(app.config["UPLOAD_FOLDER"])

    employee_id = session.get("employee_id")
    employee_name = session.get("employee_name")
    
    # These match the 'formData.append' keys in your JS
    date = request.form.get("date")
    amount = request.form.get("amount")
    category = request.form.get("category")
    file = request.files.get("proof")

    if not file or file.filename == "":
        return jsonify({"success": False, "error": "No file uploaded"})

    try:
        # Generate hash for duplicate check
        file_content = file.read()
        file_hash = hashlib.md5(file_content).hexdigest()
        file.seek(0) # Reset pointer so file.save() works

        # Check for duplicates in CSV
        if os.path.exists(EXPENSE_FILE):
            with open(EXPENSE_FILE, "r") as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) > 9 and row[9] == file_hash:
                        return jsonify({"success": False, "error": "This proof has already been submitted!"})

        # Save file with unique timestamp
        filename = secure_filename(f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
        file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        # Write to CSV
        with open(EXPENSE_FILE, "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow([employee_id, employee_name, date, amount, category, filename, "Pending", "", "", file_hash, "0"])

        return jsonify({"success": True})
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({"success": False, "error": "Server error during submission"})

# In app.py - Update the get_expenses route
@app.route("/get_expenses")
def get_expenses():
    expenses = []
    with open(EXPENSE_FILE, "r") as f:
        reader = csv.reader(f)
        for index, row in enumerate(reader):
            if row:
                while len(row) < 11: row.append("0")
                expenses.append({
                    "id": index,          # FIX: Changed "ID" to "id" to match JS
                    "emp_id": row[0],
                    "name": row[1],
                    "date": row[2],
                    "amount": row[3],
                    "category": row[4],
                    "proof": row[5],
                    "status": row[6],
                    "approval_date": row[7],
                    "comment": row[8],
                    "rejection_count": row[10]
                })
    return jsonify(expenses)

from datetime import datetime

@app.route("/update_status", methods=["POST"])
def update_status():
    if not session.get("manager_logged_in"):
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json
    try:
        expense_id = int(data["id"])
        new_status = data["status"]
        comment = data.get("comment", "")

        # 1. Load all expenses from the file
        rows = []
        with open(EXPENSE_FILE, "r") as f:
            rows = list(csv.reader(f))

        if 0 <= expense_id < len(rows):
            # Capture the Employee ID (EM-CODE) from the expense record
            emp_id_from_expense = rows[expense_id][0] 
            emp_name = rows[expense_id][1]
            
            # Update the specific expense record columns
            while len(rows[expense_id]) < 9: rows[expense_id].append("")
            rows[expense_id][6] = new_status
            # Handle rejection count
            while len(rows[expense_id]) < 11:
                rows[expense_id].append("0")

            if new_status == "Rejected":
                current_count = int(rows[expense_id][10])
                rows[expense_id][10] = str(current_count + 1)

            rows[expense_id][7] = datetime.now().strftime("%d-%m-%Y")
            rows[expense_id][8] = comment

            # 2. Find the Employee's registered email
            receiver_email = ""
            with open(EMPLOYEE_FILE, "r") as f_emp:
                emp_reader = csv.reader(f_emp)
                for emp_row in emp_reader:
                    # Match EM-CODE (Index 4) to find Email (Index 5)
                    if len(emp_row) > 5 and emp_row[4] == emp_id_from_expense:
                        receiver_email = emp_row[5]
                        break

            # 3. Send the Notification Email
            if receiver_email:
                try:
                    msg_text = f"Hello {emp_name},\n\nYour expense claim ({emp_id_from_expense}) has been {new_status}."
                    if new_status == "Rejected":
                        msg_text += f"\n\nManager Comment: {comment}"
                    
                    msg = MIMEText(msg_text)
                    msg["Subject"] = f"Expense Notification: {new_status}"
                    msg["From"] = f"ExpenseApp System <{SENDER_EMAIL}>"
                    msg["To"] = receiver_email

                    server = smtplib.SMTP("smtp.gmail.com", 587, timeout=10)
                    server.starttls()
                    server.login(SENDER_EMAIL, SENDER_PASSWORD)
                    server.send_message(msg)
                    server.quit()
                except Exception as mail_err:
                    print(f"Mail Notification Failed: {mail_err}")

            # 4. Save updated data back to CSV
            with open(EXPENSE_FILE, "w", newline="") as f:
                csv.writer(f).writerows(rows)

            return jsonify({"success": True})
            
    except Exception as e:
        print(f"Status Update Error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

# DASHBOARD STATS

@app.route("/dashboard_stats")
def dashboard_stats():

    if not session.get("manager_logged_in"):
        return jsonify({"error": "Unauthorized"}), 403

    total_employees = 0
    pending_employees = 0
    pending_expenses = 0

    # Read employee file
    with open(EMPLOYEE_FILE, "r") as f:
        reader = csv.reader(f)
        for row in reader:
            if row and len(row) >= 3:
                status = row[2].strip()

                if status == "Approved":
                    total_employees += 1
                elif status == "Pending":
                    pending_employees += 1

    # Read expense file
    with open(EXPENSE_FILE, "r") as f:
        reader = csv.reader(f)
        for row in reader:
            if row and len(row) >= 7:
                if row[6].strip() == "Pending":
                    pending_expenses += 1

    return jsonify({
        "total_employees": total_employees,
        "pending_employees": pending_employees,
        "pending_expenses": pending_expenses
    })

# PAST EXPENSES

@app.route("/past_expenses")
def past_expenses():

    if not session.get("manager_logged_in"):
        return redirect("/manager_login")

    expenses = []

    with open(EXPENSE_FILE, "r") as f:
        reader = csv.reader(f)
        for row in reader:
            if row and len(row) >= 5 and row[4] != "Pending":
                expenses.append(row)

    return render_template("past_expenses.html",
                           expenses=expenses)

# HELP

@app.route("/help")
def help_page():

    if not session.get("manager_logged_in"):
        return redirect("/manager_login")

    return render_template("help.html")

# LOGOUT

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# Partial Routes

@app.route("/manager_expenses_partial")
def manager_expenses_partial():
    if not session.get("manager_logged_in"):
        return redirect("/manager_login")
    return render_template("partials/expenses_partial.html")


@app.route("/manage_employees_partial")
def manage_employees_partial():
    if not session.get("manager_logged_in"):
        return redirect("/manager_login")

    # FIX: Initialize the list name clearly to avoid NameError
    employees_list = [] 

    with open(EMPLOYEE_FILE, "r") as f:
        reader = csv.reader(f)
        for index, row in enumerate(reader):
            if row:
                # Ensure we capture the email at index 5
                employees_list.append({
                    "id": index,
                    "name": row[0],
                    "status": row[2] if len(row) > 2 else "Pending",
                    "date": row[3] if len(row) > 3 else "N/A",
                    "emp_code": row[4] if len(row) > 4 else "",
                    "email": row[5] if len(row) > 5 else "N/A" # Capture Email field
                })

    # FIX: Use 'employees_list' here to match the initialization above
    employees_list.sort(
        key=lambda x: (
            0 if x["status"] == "Approved" else
            1 if x["status"] == "Rejected" else
            2,
            x["name"].lower()
        )
    )

    # Pass 'employees_list' to the template as 'employees'
    return render_template(
        "partials/manage_employees_partial.html",
        employees=employees_list
    )

# In app.py - Update past_expenses and past_expenses_partial routes
@app.route("/past_expenses_partial")
def past_expenses_partial():
    expenses = []
    with open(EXPENSE_FILE, "r") as f:
        for row in csv.reader(f):
            # FIX: Change index 4 to 6 (Status column)
            if row and len(row) > 6 and row[6] != "Pending":
                expenses.append(row)
    return render_template("partials/past_expenses_partial.html", expenses=expenses)

@app.route("/employee_details/<int:emp_index>")
def employee_details(emp_index):

    if not session.get("manager_logged_in"):
        return jsonify({"error": "Unauthorized"}), 403

    employee = None
    expenses_list = []

    total_uploaded = 0
    accepted_count = 0
    rejected_count = 0

    # Get employee details
    with open(EMPLOYEE_FILE, "r") as f:
        rows = list(csv.reader(f))

        if 0 <= emp_index < len(rows):
            row = rows[emp_index]

            employee = {
                "emp_id": row[4] if len(row) > 4 else "",
                "name": row[0],
                "email": row[5],
                "date": row[3]
            }

    # Get employee expenses
    with open(EXPENSE_FILE, "r") as f:
        for row in csv.reader(f):

            if row and row[0] == employee["emp_id"]:

                total_uploaded += 1

                category = row[4]
                amount = row[3]
                action_date = row[7] if len(row) > 7 else "-"
                status = row[6] if len(row) > 6 else "Pending"
                

                if status == "Approved":
                    accepted_count += 1
                elif status == "Rejected":
                    rejected_count += 1

                expenses_list.append({
                    "category": category,
                    "amount": amount,
                    "action_date": action_date,
                    "status": status
                })

    return jsonify({
    "employee": employee,
    "total_uploaded": total_uploaded,
    "accepted_count": accepted_count,
    "rejected_count": rejected_count,
    "expenses": expenses_list
})

@app.route("/delete_employee", methods=["POST"])
def delete_employee():

    if not session.get("manager_logged_in"):
        return jsonify({"error": "Unauthorized"}), 403

    emp_id = int(request.form.get("id"))

    rows = []

    with open(EMPLOYEE_FILE, "r") as f:
        rows = list(csv.reader(f))

    if 0 <= emp_id < len(rows):
        rows.pop(emp_id)

    with open(EMPLOYEE_FILE, "w", newline="") as f:
        csv.writer(f).writerows(rows)

    return jsonify({"success": True})


@app.route("/help_partial")
def help_partial():
    if not session.get("manager_logged_in"):
        return redirect("/manager_login")
    return render_template("partials/help_partial.html")

# RUN

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)