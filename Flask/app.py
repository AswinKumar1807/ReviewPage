from flask import Flask, request, jsonify, render_template, redirect, url_for

import mysql.connector
import json

app = Flask(__name__)

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

@app.route('/')
def home():
    return render_template('waiter.html')

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


# Update the backend logic to handle submission of waiter details
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






@app.route('/data.json')
def get_api_key():
    with open('static/data.json') as f:
        data = json.load(f)
    return jsonify(data)

if __name__ == '__main__':
    app.run()
