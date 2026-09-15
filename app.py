from flask import Flask, request, jsonify
from flask_cors import CORS
from db import (
    init_db, get_drinks, create_order, add_order_items_batch, get_user_orders,
    register_user, get_user_by_email, get_user_by_phone, get_user_by_id,
    verify_password, generate_token, tokens
)

app = Flask(__name__)
CORS(app)

init_db()


def get_token_user(token):
    return tokens.get(token)


def require_auth(f):
    def decorated_function(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Не авторизован'}), 401

        user_id = get_token_user(token)
        if not user_id:
            return jsonify({'error': 'Неверный токен'}), 401

        return f(user_id, *args, **kwargs)

    decorated_function.__name__ = f.__name__
    return decorated_function


@app.route('/register', methods=['POST'])
def api_register():
    try:
        data = request.get_json()

        name = data.get('name', '').strip()
        email = data.get('email', '').strip()
        phone = data.get('phone', '').strip()
        password = data.get('password', '').strip()

        if not name or not email or not phone or not password:
            return jsonify({'error': 'Заполните все поля'}), 400

        if len(password) < 4:
            return jsonify({'error': 'Пароль должен быть не менее 4 символов'}), 400

        user_id = register_user(name, email, phone, password)

        if not user_id:
            return jsonify({'error': 'Email или телефон уже зарегистрированы'}), 400

        return jsonify({
            'success': True,
            'message': 'Регистрация успешна',
            'user_id': user_id
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/login', methods=['POST'])
def api_login():
    try:
        data = request.get_json()

        login = data.get('login', '').strip()
        password = data.get('password', '').strip()

        if not login or not password:
            return jsonify({'error': 'Введите логин и пароль'}), 400

        user = None
        if '@' in login:
            user = get_user_by_email(login)
        else:
            user = get_user_by_phone(login)

        if not user:
            return jsonify({'error': 'Пользователь не найден'}), 401

        if not verify_password(user['password_hash'], password):
            return jsonify({'error': 'Неверный пароль'}), 401

        token = generate_token()
        tokens[token] = user['id']

        return jsonify({
            'success': True,
            'token': token,
            'user_id': user['id'],
            'name': user['name'],
            'email': user['email'],
            'phone': user['phone']
        }), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/logout', methods=['POST'])
def api_logout():
    try:
        token = request.headers.get('Authorization')
        if token and token in tokens:
            del tokens[token]

        return jsonify({'success': True}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/profile', methods=['GET'])
@require_auth
def api_profile(user_id):
    try:
        user = get_user_by_id(user_id)
        if not user:
            return jsonify({'error': 'Пользователь не найден'}), 404

        return jsonify(user), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/drinks', methods=['GET'])
def api_get_drinks():
    try:
        return jsonify(get_drinks()), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/order', methods=['POST'])
@require_auth
def api_create_order(user_id):
    try:
        data = request.get_json()

        items = data.get('items', [])
        total_price = data.get('total_price', 0)
        payment_method_id = data.get('payment_method_id')
        name = data.get('name', '').strip() or None
        phone = data.get('phone', '').strip() or None
        address = data.get('address', '').strip() or None

        if not items:
            return jsonify({'error': 'Корзина пуста'}), 400

        if not payment_method_id:
            return jsonify({'error': 'Выберите способ оплаты'}), 400

        # Создаём заказ
        order_id = create_order(user_id, total_price, payment_method_id, name, phone, address)

        # Подготавливаем товары для пакетной вставки
        order_items = []
        for item in items:
            order_items.append({
                'order_id': order_id,
                'drink_id': item['id'],
                'quantity': item['quantity'],
                'price': item['price']
            })

        # Вставляем все товары одной транзакцией
        add_order_items_batch(order_items)

        return jsonify({
            'success': True,
            'order_id': order_id
        }), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/orders', methods=['GET'])
@require_auth
def api_get_orders(user_id):
    try:
        orders = get_user_orders(user_id)
        return jsonify(orders), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)