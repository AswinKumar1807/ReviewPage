from flask import Flask, request, jsonify, render_template, redirect, url_for, session, flash
import openpyxl
import os
import bcrypt
import mysql.connector
import json
import secrets

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Database configuration
db_config = {
    'host': '184.168.113.121',
    'port': 3306,
    'user': 'ReviewAdmin',
    'passwd': 'Thedon@1999Thedon@1999',
    'database': 'ReviewApp'
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

def create_tables():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Create Credentials table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Credentials (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(255) UNIQUE NOT NULL,
                password VARCHAR(255) NOT NULL,
                waiter_name VARCHAR(255),
                phone_number VARCHAR(20) UNIQUE
            )
        """)

        # Create Admin table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Admin (
                id INT AUTO_INCREMENT PRIMARY KEY,
                `Table` INT UNIQUE NOT NULL,
                Dish VARCHAR(255) NOT NULL
            )
        """)

        # Create WaiterDetails table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS WaiterDetails (
                id INT AUTO_INCREMENT PRIMARY KEY,
                waiter_name VARCHAR(255) NOT NULL,
                working_shift VARCHAR(10) NOT NULL,
                table_served INT NOT NULL,
                dish_served VARCHAR(255) NOT NULL
            )
        """)

        # Commit and close cursor
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error creating tables: {str(e)}")

create_tables()

@app.route('/')
def home():
    # Clear existing flash messages
    if '_flashes' in session:
        session['_flashes'] = []

    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password').encode('utf-8')

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "SELECT password FROM Credentials WHERE username = %s"
        cursor.execute(query, (username,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if result and bcrypt.checkpw(password, result[0].encode('utf-8')):
            session['username'] = username
            token = secrets.token_urlsafe(16)
            session['token'] = token
            return redirect(url_for('waiter', token=token))
        else:
            flash('Invalid username or password', 'error')
            return redirect(url_for('home'))
    except Exception as e:
        flash(f'Failed to login: {str(e)}', 'error')
        return redirect(url_for('home'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password').encode('utf-8')
        waiter_name = request.form.get('waiter_name')
        phone_number = request.form.get('phone_number')
        hashed_password = bcrypt.hashpw(password, bcrypt.gensalt()).decode('utf-8')

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS Credentials (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(255) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    waiter_name VARCHAR(255),
                    phone_number VARCHAR(20) UNIQUE
                )
            """)
            query = "INSERT INTO Credentials (username, password, waiter_name, phone_number) VALUES (%s, %s, %s, %s)"
            cursor.execute(query, (username, hashed_password, waiter_name, phone_number))
            conn.commit()
            cursor.close()
            conn.close()
            flash('Account created successfully! Please log in.', 'success')
            return redirect(url_for('home'))
        except mysql.connector.Error as err:
            if err.errno == 1054:
                flash('Error creating account: Required column not found. Please contact administrator.', 'error')
            elif err.errno == 1062:
                flash('User already exists. Please login.', 'error')
            else:
                flash(f'Failed to sign up: {str(err)}', 'error')
            return redirect(url_for('signup'))  # Redirect to signup route for displaying error messages

    return render_template('signup.html', error_messages=[])  # Pass empty list to render_template

@app.route('/waiter/<token>')
def waiter(token):
    if 'username' in session and 'token' in session and session['token'] == token:
        return render_template('waiter.html', username=session['username'])
    else:
        return redirect(url_for('home'))

@app.route('/customer<int:table_number>')
def customer(table_number):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "SELECT Dish FROM Admin WHERE `Table` = %s"
        cursor.execute(query, (table_number,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()

        if result:
            dish = result[0]
            return render_template('customer.html', table_number=table_number, dish=dish)
        else:
            return jsonify({'success': False, 'message': f'No dish found for table {table_number}'}), 404
    except Exception as e:
        return jsonify({'success': False, 'message': f'Failed to fetch dish review: {str(e)}'}), 500

@app.route('/submit_dish', methods=['POST'])
def submit_dish():
    table_number = request.form.get('table_number')
    dish_name = request.form.get('dish_name')
    waiter_name = request.form.get('waiter_name')
    working_shift = request.form.get('working_shift')

    if table_number and dish_name and waiter_name and working_shift:
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # Check if the table already exists in the Admin table
            query = "SELECT * FROM Admin WHERE `Table` = %s"
            cursor.execute(query, (table_number,))
            result = cursor.fetchone()

            if result:
                # If a dish already exists for the table, update it
                update_query = "UPDATE Admin SET Dish = %s WHERE `Table` = %s"
                cursor.execute(update_query, (dish_name, table_number))
            else:
                # If no dish exists for the table, insert a new record
                insert_query = "INSERT INTO Admin (`Table`, Dish) VALUES (%s, %s)"
                cursor.execute(insert_query, (table_number, dish_name))

            # Insert waiter details into WaiterDetails table
            waiter_query = "INSERT INTO WaiterDetails (waiter_name, working_shift, table_served, dish_served) VALUES (%s, %s, %s, %s)"
            cursor.execute(waiter_query, (waiter_name, working_shift, table_number, dish_name))

            conn.commit()
            cursor.close()
            conn.close()
            return jsonify({'success': True, 'message': 'Dish submitted successfully!'}), 200
        except Exception as e:
            print(f'Error during database operation: {str(e)}')  # Log the error
            return jsonify({'success': False, 'message': f'Failed to submit dish: {str(e)}'}), 500
    else:
        return jsonify({'success': False, 'message': 'Invalid input: Table number, dish name, waiter name, or working shift is missing'}), 400



if __name__ == '__main__':
    app.run(debug=False)
