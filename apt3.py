from flask import Flask, request, render_template, redirect, url_for, flash, session, jsonify
from pymongo import MongoClient
import bcrypt
from bson.objectid import ObjectId
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# MongoDB connection
client = MongoClient('mongodb://localhost:27017/')
db = client['stock_management']
users_collection = db['users']
products_collection = db['Product']
suppliers_collection = db['Supplier']
deliveries_collection = db['Delivery']
customers_collection = db['Customer']
orders_collection = db['Order']
activities_collection = db['activities']


def log_activity(user_id, username, action, description, details=None):
    activity = {
        "user_id": user_id,
        "username": username,
        "action": action,
        "description": description,
        "timestamp": datetime.utcnow(),
        "details": details if details else {}
    }
    activities_collection.insert_one(activity)


@app.route('/')
def home():
    return render_template('login.html')


@app.route('/login', methods=['POST'])
def login():
    username = request.form.get('username')
    password = request.form.get('password')

    user = users_collection.find_one({'username': username})
    if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
        log_activity(user_id=user['_id'], username=user['username'], action="login", description="User logged in")
        flash('Login successful!', 'success')
        session['username'] = user['username']
        session['role'] = user['role']
        if user['role'] == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif user['role'] == 'employee':
            return redirect(url_for('employee_dashboard'))
    else:
        flash('Invalid username or password.', 'error')
        return redirect(url_for('home'))


@app.route('/admin_dashboard')
def admin_dashboard():
    if 'username' in session and session['role'] == 'admin':
        users = users_collection.find()
        return render_template('admin_dashboard.html', users=users, username=session['username'])
    else:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('home'))


@app.route('/channel_log')
def channel_log():
    if 'username' not in session or session.get('role') != 'admin':
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('home'))

    # Fetch the latest activities
    activities = list(activities_collection.find().sort("timestamp", -1))  # Sort by latest first
    return render_template('channel_log.html', activities=activities)


@app.route('/employee_dashboard')
def employee_dashboard():
    if 'username' in session and session['role'] == 'employee':
        return render_template('employee_dashboard.html', username=session['username'])
    else:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('home'))


@app.route('/products', methods=['GET', 'POST'])
def products():
    if request.method == 'POST':
        search_criteria = request.form.get('search_criteria')
        search_query = request.form.get('search')

        if search_query:
            if search_criteria == "all":
                products = list(products_collection.find({
                    "$or": [
                        {"productName": {"$regex": search_query, "$options": "i"}},
                        {"brand": {"$regex": search_query, "$options": "i"}},
                        {"category": {"$regex": search_query, "$options": "i"}},
                        {"sub_category": {"$regex": search_query, "$options": "i"}},
                        {"sub_subcategory": {"$regex": search_query, "$options": "i"}},
                        {"supplier": {"$regex": search_query, "$options": "i"}},
                        {"consumer_type": {"$regex": search_query, "$options": "i"}}
                    ]
                }))
            else:
                products = list(db.product.find({
                    search_criteria: {"$regex": f"^{search_query}", "$options": "i"}
                }))
        else:
            products = list(products_collection.find())
    else:
        products = list(products_collection.find())

    today = datetime.now()
    expiring_soon_date = today + timedelta(days=14)
    expiring_products = list(products_collection.find({
        "expiry_Date": {
            "$exists": True,
            "$ne": "",
            "$type": "string"
        },
        "$expr": {
            "$lte": [{"$dateFromString": {"dateString": "$expiry_Date"}}, expiring_soon_date]
        }
    }))

    return render_template('products.html', products=products, expiring_products=expiring_products)


@app.route('/add_product', methods=['POST'])
def add_product():
    productID = request.form.get('productID')
    productName = request.form.get('productName')
    Brand = request.form.get('Brand')
    category = request.form.get('category')
    sub_category = request.form.get('sub_category')
    sub_subcategory = request.form.get('sub_subcategory')
    costPrice = float(request.form.get('costPrice'))
    marketPrice = float(request.form.get('marketPrice'))
    Supplier = request.form.get('Supplier')
    quantity = int(request.form.get('quantity'))
    Consumer_type = request.form.get('Consumer_type')
    expiry_Date = request.form.get('expiry_Date')

    products_collection.insert_one({
        "productID": productID,
        "productName": productName,
        "Brand": Brand,
        "category": category,
        "sub_category": sub_category,
        "sub_subcategory": sub_subcategory,
        "costPrice": costPrice,
        "marketPrice": marketPrice,
        "Supplier": Supplier,
        "quantity": quantity,
        "Consumer_type": Consumer_type,
        "expiry_Date": expiry_Date
    })

    log_activity(user_id=session.get('username'), username=session.get('username'), action="add_product",
                 description="Added a new product", details={"productID": productID, "productName": productName})
    return redirect(url_for('products'))


@app.route('/update_product/<product_id>', methods=['POST'])
def update_product(product_id):
    data = request.json
    products_collection.update_one(
        {"_id": ObjectId(product_id)},
        {"$set": {"productID": data['productID'], "productName": data['productName'], "Brand": data['Brand'],
                  "category": data['category'], "sub_category": data['sub_category'],
                  "sub_subcategory": data['sub_subcategory'], "costPrice": data['costPrice'],
                  "marketPrice": data['marketPrice'], "Supplier": data['Supplier'], "quantity": data['quantity'],
                  "Consumer_type": data['Consumer_type'], "expiry_Date": data['expiry_Date']}}
    )
    log_activity(user_id=session.get('username'), username=session.get('username'), action="update_product",
                 description="Updated a product",
                 details={"productID": data['productID'], "productName": data['productName']})
    return jsonify({"message": "Product updated successfully!"})


@app.route('/delete_product/<product_id>', methods=['POST'])
def delete_product(product_id):
    product = products_collection.find_one({"_id": ObjectId(product_id)})
    products_collection.delete_one({"_id": ObjectId(product_id)})
    log_activity(user_id=session.get('username'), username=session.get('username'), action="delete_product",
                 description="Deleted a product",
                 details={"productID": product['productID'], "productName": product['productName']})
    return redirect(url_for('products'))


@app.route('/users', methods=['GET', 'POST'])
def users():
    if request.method == 'POST':
        search_criteria = request.form.get('search_criteria')
        search_query = request.form.get('search')

        if search_query:
            if search_criteria == "all":
                users = list(db.users.find({
                    "$or": [
                        {"username": {"$regex": f"^{search_query}", "$options": "i"}},
                        {"role": {"$regex": f"^{search_query}", "$options": "i"}}
                    ]
                }))
            else:
                users = list(db.users.find({
                    search_criteria: {"$regex": f"^{search_query}", "$options": "i"}
                }))
        else:
            users = list(db.users.find())
    else:
        users = list(db.users.find())

    return render_template('users.html', users=users)


@app.route('/add_user', methods=['POST'])
def add_user():
    username = request.form.get('username')
    password = request.form.get('password').encode('utf-8')
    hashed_password = bcrypt.hashpw(password, bcrypt.gensalt())
    role = request.form.get('role')
    db.users.insert_one({
        "username": username,
        'password': hashed_password,
        "role": role
    })

    log_activity(user_id=session.get('username'), username=session.get('username'), action="add_user",
                 description="Added a new user", details={"username": username, "role": role})
    return redirect(url_for('users'))


@app.route('/update_user/<user_id>', methods=['POST'])
def update_user(user_id):
    data = request.json
    db.users.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"user_id": data['user_id'], "username": data['username'], "role": data['role']}}
    )
    log_activity(user_id=session.get('username'), username=session.get('username'), action="update_user",
                 description="Updated user info", details={"username": data['username'], "role": data['role']})
    return jsonify({"message": "User info updated successfully!"})


@app.route('/delete_user/<user_id>', methods=['POST'])
def delete_user(user_id):
    user = db.users.find_one({"_id": ObjectId(user_id)})
    db.users.delete_one({"_id": ObjectId(user_id)})
    log_activity(user_id=session.get('username'), username=session.get('username'), action="delete_user",
                 description="Deleted a user", details={"username": user['username']})
    return redirect(url_for('users'))


@app.route('/suppliers', methods=['GET', 'POST'])
def suppliers():
    if request.method == 'POST':
        search_criteria = request.form.get('search_criteria')
        search_query = request.form.get('search')

        if search_query:
            if search_criteria == "all":
                suppliers = list(suppliers_collection.find({
                    "$or": [
                        {"SID": {"$regex": f"^{search_query}", "$options": "i"}},
                        {"Sname": {"$regex": f"^{search_query}", "$options": "i"}},
                        {"Saddress": {"$regex": f"^{search_query}", "$options": "i"}},
                        {"Sphone": {"$regex": f"^{search_query}", "$options": "i"}},
                        {"Semail": {"$regex": f"^{search_query}", "$options": "i"}}
                    ]
                }))
            else:
                suppliers = list(suppliers_collection.find({
                    search_criteria: {"$regex": f"^{search_query}", "$options": "i"}
                }))
        else:
            suppliers = list(suppliers_collection.find())
    else:
        suppliers = list(suppliers_collection.find())

    return render_template('suppliers.html', suppliers=suppliers)


@app.route('/add_supplier', methods=['POST'])
def add_supplier():
    SID = request.form.get('SID')
    Sname = request.form.get('Sname')
    Saddress = request.form.get('Saddress')
    Sphone = request.form.get('Sphone')
    Semail = request.form.get('Semail')

    suppliers_collection.insert_one({
        "SID": SID,
        "Sname": Sname,
        "Saddress": Saddress,
        "Sphone": Sphone,
        "Semail": Semail
    })

    log_activity(user_id=session.get('username'), username=session.get('username'), action="add_supplier",
                 description="Added a new supplier", details={"SID": SID, "Sname": Sname})
    return redirect(url_for('suppliers'))


@app.route('/update_supplier/<SID>', methods=['POST'])
def update_supplier(SID):
    data = request.json
    db.users.update_one(
        {"_id": ObjectId(SID)},
        {"$set": {"SID": data['SID'], "Sname": data['Sname'], "Saddress": data['Saddress'], "Sphone": data['Sphone'],
                  "Semail": data['Semail']}}
    )
    log_activity(user_id=session.get('username'), username=session.get('username'), action="update_supplier",
                 description="Updated supplier info", details={"SID": data['SID'], "Sname": data['Sname']})
    return jsonify({"message": "Supplier info updated successfully!"})


@app.route('/delete_supplier/<supplier_id>', methods=['POST'])
def delete_supplier(supplier_id):
    supplier = suppliers_collection.find_one({"_id": ObjectId(supplier_id)})
    suppliers_collection.delete_one({"_id": ObjectId(supplier_id)})
    log_activity(user_id=session.get('username'), username=session.get('username'), action="delete_supplier",
                 description="Deleted a supplier", details={"SID": supplier['SID'], "Sname": supplier['Sname']})
    return redirect(url_for('suppliers'))


@app.route('/deliveries', methods=['GET', 'POST'])
def deliveries():
    if request.method == 'POST':
        search_criteria = request.form.get('search_criteria')
        search_query = request.form.get('search')

        if search_query:
            if search_criteria == "all":
                deliveries = list(deliveries_collection.find({
                    "$or": [
                        {"D_id": {"$regex": f"^{search_query}", "$options": "i"}},
                        {"C_id": {"$regex": f"^{search_query}", "$options": "i"}},
                        {"delivery_date": {"$regex": f"^{search_query}", "$options": "i"}},
                        {"delivery_address": {"$regex": f"^{search_query}", "$options": "i"}},
                        {"total_price": {"$regex": f"^{search_query}", "$options": "i"}},
                        {"Status": {"$regex": f"^{search_query}", "$options": "i"}}
                    ]
                }))
            else:
                deliveries = list(deliveries_collection.find({
                    search_criteria: {"$regex": f"^{search_query}", "$options": "i"}
                }))
        else:
            deliveries = list(deliveries_collection.find())
    else:
        deliveries = list(deliveries_collection.find())
    pending_deliveries = list(deliveries_collection.find({"Status": "Pending"}))

    return render_template('deliveries.html', deliveries=deliveries, pending_deliveries=pending_deliveries)


@app.route('/add_delivery', methods=['POST'])
def add_delivery():
    D_id = request.form.get('D_id')
    C_id = request.form.get('C_id')
    delivery_date = request.form.get('delivery_date')
    delivery_address = request.form.get('delivery_address')
    total_price = float(request.form.get('total_price'))
    Status = request.form.get('Status')
    list_of_products = request.form.getlist('list_of_products')

    deliveries_collection.insert_one({
        "D_id": D_id,
        "C_id": C_id,
        "delivery_date": delivery_date,
        "delivery_address": delivery_address,
        "total_price": total_price,
        "Status": Status,
        "list_of_products": list_of_products
    })

    delivery_details = {
        "D_id": D_id,
        "delivery_date": delivery_date,
        "delivery_address": delivery_address,
        "total_price": total_price,
        "Status": Status,
        "list_of_products": list_of_products
    }

    customers_collection.update_one(
        {"C_ID": C_id},
        {"$push": {"delivery_history": delivery_details}}
    )

    log_activity(user_id=session.get('username'), username=session.get('username'), action="add_delivery",
                 description="Added a new delivery", details={"D_id": D_id, "C_id": C_id})
    return redirect(url_for('deliveries'))


@app.route('/update_delivery/<D_id>', methods=['POST'])
def update_delivery(D_id):
    data = request.json
    deliveries_collection.update_one(
        {"_id": ObjectId(D_id)},
        {"$set": {"D_id": data['D_id'], "C_id": data['C_id'], "delivery_date": data['delivery_date'],
                  "delivery_address": data['delivery_address'], "total_price": data['total_price'],
                  "Status": data['Status'], "list_of_products": data['list_of_products']}}
    )
    log_activity(user_id=session.get('username'), username=session.get('username'), action="update_delivery",
                 description="Updated delivery info", details={"D_id": data['D_id'], "C_id": data['C_id']})
    return jsonify({"message": "Delivery info updated successfully!"})


@app.route('/delete_delivery/<delivery_id>', methods=['POST'])
def delete_delivery(delivery_id):
    delivery = deliveries_collection.find_one({"_id": ObjectId(delivery_id)})
    deliveries_collection.delete_one({"_id": ObjectId(delivery_id)})
    log_activity(user_id=session.get('username'), username=session.get('username'), action="delete_delivery",
                 description="Deleted a delivery", details={"D_id": delivery['D_id'], "C_id": delivery['C_id']})
    return redirect(url_for('deliveries'))


@app.route('/customers', methods=['GET', 'POST'])
def customers():
    if request.method == 'POST':
        search_criteria = request.form.get('search_criteria')
        search_query = request.form.get('search')

        if search_query:
