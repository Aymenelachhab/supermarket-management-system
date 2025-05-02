from pymongo import MongoClient
import bcrypt

client = MongoClient('mongodb://localhost:27017/')
db = client['stock_management']
users_collection = db['users']

# Hash a password
password = 'ahmed123'.encode('utf-8')
hashed_password = bcrypt.hashpw(password, bcrypt.gensalt())

# Store the hashed password in MongoDB
users_collection.insert_one({
    'username': 'ahmed',
    'password': hashed_password,
    'role': 'employee'
})