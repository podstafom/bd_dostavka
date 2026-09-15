import pyodbc
import hashlib
import secrets

DB_CONFIG = {
    'server': 'DESKTOP-ER9KDDJ',
    'database': 'drinks_delivery',
    'driver': 'ODBC Driver 17 for SQL Server',
}

tokens = {}


def hash_password(password):
    salt = secrets.token_hex(32)
    key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
    return salt + key.hex()


def verify_password(stored_hash, password):
    try:
        salt = stored_hash[:64]
        stored_key = stored_hash[64:]
        key = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return key.hex() == stored_key
    except:
        return False


def generate_token():
    return secrets.token_hex(32)


def get_db():
    conn_str = (
        f"DRIVER={{{DB_CONFIG['driver']}}};"
        f"SERVER={DB_CONFIG['server']};"
        f"Database={DB_CONFIG['database']};"
        f"Trusted_Connection=yes;"
    )
    return pyodbc.connect(conn_str)


def _column_exists(cursor, table, column):
    cursor.execute("""
        SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = ? AND COLUMN_NAME = ?
    """, (table, column))
    return cursor.fetchone()


def _table_exists(cursor, table):
    cursor.execute("""
        SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES
        WHERE TABLE_NAME = ?
    """, (table,))
    return cursor.fetchone() is not None


def _column_is_nullable(cursor, table, column):
    cursor.execute("""
        SELECT IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = ? AND COLUMN_NAME = ?
    """, (table, column))
    row = cursor.fetchone()
    return row is not None and row[0] == 'YES'


def _make_column_nullable(cursor, table, column):
    info = _column_exists(cursor, table, column)
    if not info:
        return False
    col_name, data_type, max_len = info
    if data_type in ('varchar', 'nvarchar', 'char', 'nchar') and max_len:
        type_str = f"{data_type}({max_len})"
    elif data_type in ('decimal', 'numeric') and max_len:
        type_str = f"{data_type}(10,2)"  # fallback
    else:
        type_str = data_type
    cursor.execute(f"ALTER TABLE {table} ALTER COLUMN {column} {type_str} NULL")
    return True


def _ensure_orders_schema(cursor):
    required_not_null = {'id', 'user_id', 'total_price'}
    our_columns = {'payment_method_id', 'status', 'created_at', 'name', 'phone', 'address'}
    ignore_columns = {'items'}

    cursor.execute("""
        SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH, NUMERIC_PRECISION, NUMERIC_SCALE
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_NAME = 'orders'
    """)
    for row in cursor.fetchall():
        col_name = row[0]
        if col_name in required_not_null:
            continue
        if col_name in ignore_columns:
            continue
        if not _column_is_nullable(cursor, 'orders', col_name):
            data_type = row[1]
            char_len = row[2]
            num_prec = row[3]
            num_scale = row[4]
            if data_type in ('nvarchar', 'varchar', 'nchar', 'char') and char_len and char_len > 0:
                if char_len == -1:
                    type_str = f"{data_type}(MAX)"
                else:
                    type_str = f"{data_type}({char_len})"
            elif data_type in ('decimal', 'numeric') and num_prec is not None:
                scale = num_scale if num_scale is not None else 0
                type_str = f"{data_type}({num_prec},{scale})"
            else:
                type_str = data_type
            cursor.execute(f"ALTER TABLE orders ALTER COLUMN {col_name} {type_str} NULL")
            print(f"Столбец {col_name} в orders теперь NULLABLE")

    for col, col_type in [('payment_method_id', 'INT'), ('status', "NVARCHAR(50)"),
                          ('created_at', 'DATETIME'), ('name', 'NVARCHAR(255)'),
                          ('phone', 'NVARCHAR(20)'), ('address', 'NVARCHAR(MAX)')]:
        if not _column_exists(cursor, 'orders', col):
            cursor.execute(f"ALTER TABLE orders ADD {col} {col_type} NULL")
            print(f"Столбец {col} добавлен в orders")


def init_db():
    conn = get_db()
    cursor = conn.cursor()

    if not _table_exists(cursor, 'users'):
        cursor.execute('''
            CREATE TABLE users (
                id INT PRIMARY KEY IDENTITY(1,1),
                name NVARCHAR(255) NOT NULL,
                email NVARCHAR(255) NOT NULL UNIQUE,
                phone NVARCHAR(20) NOT NULL UNIQUE,
                password_hash NVARCHAR(MAX) NOT NULL,
                created_at DATETIME DEFAULT GETDATE()
            )
        ''')
        print("Таблица users создана")

    if not _table_exists(cursor, 'drinks'):
        cursor.execute('''
            CREATE TABLE drinks (
                id INT PRIMARY KEY IDENTITY(1,1),
                name NVARCHAR(255) NOT NULL,
                price DECIMAL(10,2) NOT NULL,
                description NVARCHAR(MAX),
                created_at DATETIME DEFAULT GETDATE()
            )
        ''')

        drinks = [
            ('Есенархыз', 150.00, 'Минеральная вода 0.5л'),
            ('Априганит', 350.00, 'Кокосовая вода 0.25л'),
            ('Фабризио', 480.00, 'Безалкогольный виски 0.4л'),
            ('Кристальный путь', 100.00, 'Вода 0.5л'),
            ('Грязный Джо', 250.00, 'Безалкогольный спирт 0.2л'),
            ('Антуфьеванин', 500.00, 'Безалкогольное шампанское 500ml'),
            ('Ивановчиканин', 650.00, 'Безалкогольный самогон 0.5л'),
            ('Скрынчикан', 550.00, 'Безалкогольное вино 0.6л'),
        ]

        for name, price, desc in drinks:
            cursor.execute(
                'INSERT INTO drinks (name, price, description) VALUES (?, ?, ?)',
                (name, price, desc)
            )
        print("Таблица drinks создана")

    if not _table_exists(cursor, 'payment_methods'):
        cursor.execute('''
            CREATE TABLE payment_methods (
                id INT PRIMARY KEY IDENTITY(1,1),
                name NVARCHAR(100) NOT NULL
            )
        ''')

        payment_methods = [
            ('Карта',),
            ('Наличные',),
            ('Онлайн-оплата',)
        ]

        for method in payment_methods:
            cursor.execute(
                'INSERT INTO payment_methods (name) VALUES (?)',
                method
            )
        print("Таблица payment_methods создана")

    if not _table_exists(cursor, 'orders'):
        cursor.execute('''
            CREATE TABLE orders (
                id INT PRIMARY KEY IDENTITY(1,1),
                user_id INT NOT NULL,
                total_price DECIMAL(10,2) NOT NULL,
                payment_method_id INT,
                status NVARCHAR(50) DEFAULT 'оформлено',
                created_at DATETIME DEFAULT GETDATE(),
                name NVARCHAR(255) NULL,
                phone NVARCHAR(20) NULL,
                address NVARCHAR(MAX) NULL,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (payment_method_id) REFERENCES payment_methods(id)
            )
        ''')
        print("Таблица orders создана")
    else:
        _ensure_orders_schema(cursor)

    if not _table_exists(cursor, 'order_items'):
        cursor.execute('''
            CREATE TABLE order_items (
                id INT PRIMARY KEY IDENTITY(1,1),
                order_id INT NOT NULL,
                drink_id INT NOT NULL,
                quantity INT NOT NULL,
                price DECIMAL(10,2) NOT NULL,
                FOREIGN KEY (order_id) REFERENCES orders(id),
                FOREIGN KEY (drink_id) REFERENCES drinks(id)
            )
        ''')
        print("Таблица order_items создана")

    conn.commit()
    conn.close()


def get_drinks():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, price, description FROM drinks')
    rows = cursor.fetchall()
    conn.close()

    return [
        {'id': r[0], 'name': r[1], 'price': float(r[2]), 'description': r[3]}
        for r in rows
    ]


def register_user(name, email, phone, password):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT id FROM users WHERE email = ? OR phone = ?', (email, phone))
    if cursor.fetchone():
        conn.close()
        return None

    password_hash = hash_password(password)
    cursor.execute(
        'INSERT INTO users (name, email, phone, password_hash) VALUES (?, ?, ?, ?)',
        (name, email, phone, password_hash)
    )

    cursor.execute('SELECT @@IDENTITY as last_id')
    user_id = cursor.fetchone()[0]

    conn.commit()
    conn.close()

    return int(user_id)


def get_user_by_email(email):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, email, phone, password_hash FROM users WHERE email = ?', (email,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return {
        'id': row[0],
        'name': row[1],
        'email': row[2],
        'phone': row[3],
        'password_hash': row[4]
    }


def get_user_by_phone(phone):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, email, phone, password_hash FROM users WHERE phone = ?', (phone,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return {
        'id': row[0],
        'name': row[1],
        'email': row[2],
        'phone': row[3],
        'password_hash': row[4]
    }


def get_user_by_id(user_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, email, phone FROM users WHERE id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return {
        'id': row[0],
        'name': row[1],
        'email': row[2],
        'phone': row[3]
    }


def create_order(user_id, total_price, payment_method_id, name=None, phone=None, address=None, status='оформлено'):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        '''INSERT INTO orders (user_id, total_price, payment_method_id, name, phone, address, status)
           VALUES (?, ?, ?, ?, ?, ?, ?)''',
        (user_id, total_price, payment_method_id, name, phone, address, status)
    )

    cursor.execute('SELECT @@IDENTITY as last_id')
    order_id = cursor.fetchone()[0]

    conn.commit()
    conn.close()

    return int(order_id)


def add_order_item(order_id, drink_id, quantity, price):
    """Добавляет один товар в заказ (для обратной совместимости)"""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        'INSERT INTO order_items (order_id, drink_id, quantity, price) VALUES (?, ?, ?, ?)',
        (order_id, drink_id, quantity, price)
    )

    conn.commit()
    conn.close()


def add_order_items_batch(items):
    """Добавляет несколько товаров в заказ одной транзакцией"""
    if not items:
        return

    conn = get_db()
    cursor = conn.cursor()

    for item in items:
        cursor.execute(
            'INSERT INTO order_items (order_id, drink_id, quantity, price) VALUES (?, ?, ?, ?)',
            (item['order_id'], item['drink_id'], item['quantity'], item['price'])
        )

    conn.commit()
    conn.close()


def get_user_orders(user_id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        '''SELECT id, total_price, payment_method_id, status, created_at, name, phone, address
           FROM orders WHERE user_id = ? ORDER BY created_at DESC''',
        (user_id,)
    )
    orders = cursor.fetchall()

    result = []
    for order in orders:
        order_id = order[0]

        cursor.execute(
            'SELECT oi.id, oi.drink_id, d.name, oi.quantity, oi.price FROM order_items oi JOIN drinks d ON oi.drink_id = d.id WHERE oi.order_id = ?',
            (order_id,)
        )
        items = cursor.fetchall()

        payment_method = 'Не указана'
        if order[2] is not None:
            cursor.execute(
                'SELECT name FROM payment_methods WHERE id = ?',
                (order[2],)
            )
            payment_row = cursor.fetchone()
            if payment_row:
                payment_method = payment_row[0]

        items_list = [
            {
                'id': item[1],
                'name': item[2],
                'quantity': item[3],
                'price': float(item[4])
            }
            for item in items
        ]

        result.append({
            'id': order_id,
            'total_price': float(order[1]),
            'payment_method': payment_method,
            'status': order[3] if order[3] else 'оформлено',
            'created_at': order[4].isoformat() if order[4] else None,
            'name': order[5],
            'phone': order[6],
            'address': order[7],
            'items': items_list
        })

    conn.close()
    return result