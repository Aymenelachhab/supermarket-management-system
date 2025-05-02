from pymongo import MongoClient
import bcrypt

# Connect to MongoDB
client = MongoClient('mongodb://localhost:27017/')  # Replace with your MongoDB connection string
db = client['stock_management']  # Replace with your database name
users_collection = db['users']  # Replace with your collection name

# Function to create a new user
def create_user(username, password):
    # Hash the password
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    # Insert the user into the MongoDB collection
    user = {
        'username': username,
        'password': hashed_password
    }
    result = users_collection.insert_one(user)

    if result.inserted_id:
        print(f"User '{username}' created successfully!")
    else:
        print("Failed to create user.")

# Example usage
if __name__ == '__main__':
    username = input("Enter username: ")
    password = input("Enter password: ")
    create_user(username, password)