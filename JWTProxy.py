from flask import Flask, request, jsonify
import jwt
import requests
import os

app = Flask(__name__)

SECRET_KEY_FILE = 'secret_key.txt'
BACKEND_URL = 'http://localhost:8000'

def get_secret_key():
    if os.path.exists(SECRET_KEY_FILE):
        with open(SECRET_KEY_FILE, 'r') as f:
            return f.read()
    else:
        secret_key = generate_secret_key()
        with open(SECRET_KEY_FILE, 'w') as f:
            f.write(secret_key)
        return secret_key

def generate_secret_key():
    return os.urandom(32).hex()

SECRET_KEY = get_secret_key()

@app.route('/authenticate', methods=['POST'])
def authenticate():
    # You should implement proper authentication logic here
    # For the sake of this example, assume authentication is successful
    user_id = 123
    username = 'john_doe'
    payload = {'user_id': user_id, 'username': username}
    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    return jsonify({'token': token})

@app.route('/proxy', methods=['GET', 'POST'])
def proxy():
    jwt_token = request.headers.get('Authorization', '').replace('Bearer ', '')

    try:
        decoded_token = jwt.decode(jwt_token, SECRET_KEY, algorithms=['HS256'])

        response = requests.request(
            method=request.method,
            url=f"{BACKEND_URL}{request.path}",
            headers=request.headers,
            data=request.data
        )

        return (response.content, response.status_code, response.headers.items())
    except jwt.ExpiredSignatureError:
        return jsonify({'message': 'Token has expired'}), 401
    except jwt.InvalidTokenError:
        return jsonify({'message': 'Invalid token'}), 401

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
