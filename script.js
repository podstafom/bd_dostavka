const API = 'http://localhost:5000';

let cart = [];
let allDrinks = [];
let currentOrder = null;
let currentUser = null;
let authToken = null;

//  УПРАВЛЕНИЕ СОСТОЯНИЕМ И ХРАНИЛИЩЕМ 

function saveSession(token, user) {
    localStorage.setItem('authToken', token);
    localStorage.setItem('currentUser', JSON.stringify(user));
    authToken = token;
    currentUser = user;
}

function loadSession() {
    const token = localStorage.getItem('authToken');
    const user = localStorage.getItem('currentUser');
    if (token && user) {
        authToken = token;
        currentUser = JSON.parse(user);
    }
}

function saveCart() {
    localStorage.setItem('cart', JSON.stringify(cart));
}

function loadCart() {
    const savedCart = localStorage.getItem('cart');
    if (savedCart) {
        cart = JSON.parse(savedCart);
    }
}

function getAuthHeader() {
    if (!authToken) return {};
    return { 'Authorization': authToken };
}

//   ОТПРАВКА ЗАПРОСОВ С ОБРАБОТКОЙ ОШИБОК     

async function sendWithAuth(url, options = {}) {
    const headers = {
        ...options.headers,
        ...getAuthHeader()
    };

    const response = await fetch(url, { ...options, headers });

    // Если получена ошибка 401 (Unauthorized), очищаем сессию
    if (response.status === 401) {
        localStorage.removeItem('authToken');
        localStorage.removeItem('currentUser');
        authToken = null;
        currentUser = null;
        updateAuthUI();
        throw new Error('Сессия истекла. Пожалуйста, войдите заново');
    }

    return response;
}

//   ФИЛЬТРАЦИЯ ВХОДА     

function filterPhoneInput(input) {
    input.value = input.value.replace(/\D/g, '').slice(0, 11);
}

//  АВТОРИЗАЦИЯ И РЕГИСТРАЦИЯ 

function toggleAuthForm() {
    const loginForm = document.getElementById('loginForm');
    const registerForm = document.getElementById('registerForm');
    const toggleBtn = document.getElementById('toggleBtn');
    const toggleText = document.getElementById('toggleText');

    if (loginForm.style.display === 'none') {
        loginForm.style.display = 'block';
        registerForm.style.display = 'none';
        toggleText.textContent = 'Нет аккаунта? ';
        toggleBtn.textContent = 'Зарегистрироваться';
    } else {
        loginForm.style.display = 'none';
        registerForm.style.display = 'block';
        toggleText.textContent = 'Уже есть аккаунт? ';
        toggleBtn.textContent = 'Войти';
    }

    document.getElementById('loginError').textContent = '';
    document.getElementById('registerError').textContent = '';
}

// Валидация email
function isValidEmail(email) {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
}

// Регистрация нового пользователя
async function handleRegister(event) {
    event.preventDefault();

    const name = document.getElementById('registerName').value.trim();
    const email = document.getElementById('registerEmail').value.trim();
    const phone = document.getElementById('registerPhone').value.trim();
    const password = document.getElementById('registerPassword').value.trim();
    const errorEl = document.getElementById('registerError');

    errorEl.textContent = '';

    // Валидация полей
    if (!name || !email || !phone || !password) {
        errorEl.textContent = 'Заполните все поля';
        return;
    }

    if (!isValidEmail(email)) {
        errorEl.textContent = 'Введите корректный email';
        return;
    }

    if (phone.length < 11) {
        errorEl.textContent = 'Номер телефона должен быть 11 цифр';
        return;
    }

    if (password.length < 4) {
        errorEl.textContent = 'Пароль должен быть не менее 4 символов';
        return;
    }

    try {
        const res = await fetch(`${API}/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, email, phone, password })
        });

        const result = await res.json();

        if (result.success) {
            errorEl.textContent = '';
            alert('Регистрация успешна! Пожалуйста, войдите в аккаунт');

            document.getElementById('registerForm').reset();
            toggleAuthForm();
            document.getElementById('loginInput').focus();
        } else {
            errorEl.textContent = result.error || 'Ошибка регистрации';
        }
    } catch (err) {
        errorEl.textContent = 'Ошибка подключения к серверу';
        console.error(err);
    }
}

// Вход в аккаунт
async function handleLogin(event) {
    event.preventDefault();

    const login = document.getElementById('loginInput').value.trim();
    const password = document.getElementById('loginPassword').value.trim();
    const errorEl = document.getElementById('loginError');

    errorEl.textContent = '';

    if (!login || !password) {
        errorEl.textContent = 'Введите логин и пароль';
        return;
    }

    try {
        const res = await fetch(`${API}/login`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ login, password })
        });

        const result = await res.json();

        if (result.success) {
            saveSession(result.token, {
                id: result.user_id,
                name: result.name,
                email: result.email,
                phone: result.phone
            });

            updateAuthUI();
            document.getElementById('loginForm').reset();
            showPage('menu');
            loadDrinks();
        } else {
            errorEl.textContent = result.error || 'Ошибка входа';
        }
    } catch (err) {
        errorEl.textContent = 'Ошибка подключения к серверу';
        console.error(err);
    }
}

// Выход из аккаунта
async function logoutUser() {
    if (!authToken) return;

    try {
        await fetch(`${API}/logout`, {
            method: 'POST',
            headers: getAuthHeader()
        });
    } catch (err) {
        console.error(err);
    }

    localStorage.removeItem('authToken');
    localStorage.removeItem('currentUser');
    authToken = null;
    currentUser = null;
    //  сохранять корзину при выходе

    updateAuthUI();
    showPage('menu');
}

// Обновление интерфейса в зависимости от авторизации
function updateAuthUI() {
    const historyBtn = document.getElementById('historyBtn');
    const loginBtn = document.getElementById('loginBtn');
    const logoutBtn = document.getElementById('logoutBtn');
    const userGreeting = document.getElementById('userGreeting');

    if (currentUser) {
        // Авторизован: показываем История, Выход, приветствие
        historyBtn.style.display = 'inline-block';
        loginBtn.style.display = 'none';
        logoutBtn.style.display = 'inline-block';
        userGreeting.textContent = 'Привет, ' + currentUser.name + '!';
        userGreeting.style.display = 'inline-block';
    } else {
        // Не авторизован: скрываем История, Выход, приветствие
        historyBtn.style.display = 'none';
        loginBtn.style.display = 'inline-block';
        logoutBtn.style.display = 'none';
        userGreeting.style.display = 'none';
    }
}

//   ЗАГРУЗКА И ОТОБРАЖЕНИЕ НАПИТКОВ     

async function loadDrinks() {
    const grid = document.getElementById('drinksGrid');
    const loading = document.getElementById('menuLoading');

    try {
        loading.style.display = 'block';
        grid.innerHTML = '';

        const res = await fetch(`${API}/drinks`);
        const data = await res.json();

        allDrinks = data;
        loading.style.display = 'none';

        data.forEach(drink => {
            const card = document.createElement('div');
            card.className = 'drink-card';
            card.innerHTML = `
                <div class="drink-card__image">${drink.name}</div>
                <div class="drink-card__body">
                    <h3 class="drink-card__name">${drink.name}</h3>
                    <p class="drink-card__desc">${drink.description}</p>
                    <div class="drink-card__footer">
                        <span class="drink-card__price">${drink.price} р.</span>
                        <button class="btn btn--small" onclick="addToCart(${drink.id})">+</button>
                    </div>
                </div>
            `;
            grid.appendChild(card);
        });
    } catch (err) {
        loading.innerHTML = 'Ошибка загрузки';
        console.error(err);
    }
}

//   УПРАВЛЕНИЕ КОРЗИНОЙ     

// Добавить товар в корзину (работает для всех, авторизация только при оформлении)
function addToCart(drinkId) {
    const drink = allDrinks.find(d => d.id === drinkId);
    if (!drink) return;

    const item = cart.find(i => i.id === drinkId);
    if (item) {
        item.quantity++;
    } else {
        cart.push({
            id: drink.id,
            name: drink.name,
            price: drink.price,
            quantity: 1
        });
    }

    updateCart();
    saveCart();
}

function removeFromCart(drinkId) {
    cart = cart.filter(i => i.id !== drinkId);
    updateCart();
    saveCart();
}

function changeQty(drinkId, qty) {
    const item = cart.find(i => i.id === drinkId);
    if (!item) return;

    if (qty <= 0) {
        removeFromCart(drinkId);
    } else {
        item.quantity = qty;
        updateCart();
        saveCart();
    }
}

function updateCart() {
    const cartList = document.getElementById('cartList');
    const emptyMsg = document.getElementById('emptyMessage');
    const footer = document.getElementById('cartFooter');
    const count = document.getElementById('cartCount');

    count.textContent = cart.length;

    if (cart.length === 0) {
        cartList.innerHTML = '';
        emptyMsg.style.display = 'block';
        footer.style.display = 'none';
        return;
    }

    emptyMsg.style.display = 'none';
    footer.style.display = 'block';

    cartList.innerHTML = cart.map(item => `
        <div class="cart-item">
            <div class="cart-item__info">
                <h4>${item.name}</h4>
                <p>${item.price} р. за штуку</p>
            </div>
            <div class="cart-item__controls">
                <button onclick="changeQty(${item.id}, ${item.quantity - 1})">−</button>
                <span>${item.quantity}</span>
                <button onclick="changeQty(${item.id}, ${item.quantity + 1})">+</button>
            </div>
            <div class="cart-item__total">${(item.price * item.quantity).toFixed(2)} р.</div>
            <button class="cart-item__delete" onclick="removeFromCart(${item.id})">X</button>
        </div>
    `).join('');

    const total = cart.reduce((sum, i) => sum + i.price * i.quantity, 0);
    document.getElementById('totalPrice').textContent = total.toFixed(2) + ' р.';
}

//  НАВИГАЦИЯ ПО СТРАНИЦАМ 

function showPage(name, event) {
    // Скрываем все страницы
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.getElementById(name).classList.add('active');

    // Обновляем активную кнопку в хедере
    // Используем currentTarget вместо target, чтобы всегда получать кнопку,
    // даже если клик был на вложенном элементе (например на счетчике корзины)
    document.querySelectorAll('.header__btn').forEach(b => b.classList.remove('active'));
    if (event && event.currentTarget) {
        event.currentTarget.classList.add('active');
    }

    // Загружаем нужные данные при переходе на страницу
    if (name === 'cart') updateCart();
    if (name === 'history') loadHistory();
}

//  ИСТОРИЯ ЗАКАЗОВ 

async function loadHistory() {
    const list = document.getElementById('historyList');
    const empty = document.getElementById('historyEmpty');

    list.innerHTML = '';
    empty.style.display = 'none';

    if (!currentUser) {
        empty.textContent = 'Пожалуйста, войдите в аккаунт для просмотра истории';
        empty.style.display = 'block';
        return;
    }

    try {
        const res = await sendWithAuth(`${API}/orders`);

        if (!res.ok) {
            if (res.status === 401) {
                empty.textContent = 'Сессия истекла. Пожалуйста, войдите заново';
                empty.style.display = 'block';
                return;
            }
            throw new Error('Ошибка загрузки');
        }

        const orders = await res.json();

        if (!Array.isArray(orders) || orders.length === 0) {
            empty.textContent = 'Нет заказов';
            empty.style.display = 'block';
            return;
        }

        list.innerHTML = orders.map(order => {
            let itemsHtml = '';
            if (order.items && Array.isArray(order.items)) {
                itemsHtml = order.items.map(item =>
                    '<li>' + item.name + ' x ' + item.quantity + ' = ' + (item.price * item.quantity).toFixed(2) + ' р.</li>'
                ).join('');
            }

            return `
                <div class="order-item">
                    <div class="order-item__header">
                        <strong>№${order.id}</strong>
                        <span class="order-item__date">${new Date(order.created_at).toLocaleString('ru-RU')}</span>
                    </div>
                    <div class="order-item__body">
                        <p><strong>Товары:</strong></p>
                        <ul style="margin-left: 16px; margin-bottom: 8px;">
                            ${itemsHtml}
                        </ul>
                        <p><strong>Сумма:</strong> ${order.total_price.toFixed(2)} р.</p>
                        <p><strong>Способ оплаты:</strong> ${order.payment_method}</p>
                        <p><strong>Статус:</strong> ${order.status}</p>
                    </div>
                </div>
            `;
        }).join('');
    } catch (err) {
        empty.textContent = 'Ошибка загрузки истории заказов';
        empty.style.display = 'block';
        console.error(err);
    }
}

//   ОФОРМЛЕНИЕ ЗАКАЗА     

function checkout() {
    if (cart.length === 0) {
        alert('Корзина пуста');
        return;
    }

    // Проверяем авторизацию
    if (!currentUser) {
        alert('Для оформления заказа войдите или зарегистрируйтесь');
        showPage('login');
        return;
    }

    // Автозаполняем имя и телефон из данных пользователя
    document.getElementById('orderName').value = currentUser.name;
    document.getElementById('orderPhone').value = currentUser.phone;

    const modal = document.getElementById('checkoutModal');
    modal.style.display = 'flex';

    const preview = document.getElementById('orderPreview');
    let html = '<ul>';
    let total = 0;

    cart.forEach(item => {
        const subtotal = item.price * item.quantity;
        total += subtotal;
        html += '<li>' + item.name + ' x ' + item.quantity + ' = ' + subtotal.toFixed(2) + ' р.</li>';
    });

    html += '</ul>';
    html += '<div style="margin-top: 10px;"><strong>Итого: ' + total.toFixed(2) + ' р.</strong></div>';
    preview.innerHTML = html;
}

function closeCheckout() {
    document.getElementById('checkoutModal').style.display = 'none';
}

function validatePhone(phone) {
    phone = phone.replace(/\D/g, '');

    if (phone.length === 10) {
        phone = '8' + phone;
    }

    if (phone.length !== 11) {
        return { valid: false, message: 'Номер должен быть 11 цифр' };
    }

    if (phone[0] !== '8') {
        return { valid: false, message: 'Номер должен начинаться с 8' };
    }

    return { valid: true, formatted: phone };
}

async function submitOrder(e) {
    e.preventDefault();

    if (!currentUser) {
        alert('Для оформления заказа войдите или зарегистрируйтесь');
        closeCheckout();
        showPage('login');
        return;
    }

    const name = document.getElementById('orderName').value.trim();
    const phone = document.getElementById('orderPhone').value.trim();
    const address = document.getElementById('orderAddress').value.trim();
    const paymentMethod = document.getElementById('paymentMethod').value;

    if (!name) {
        alert('Ошибка: имя пользователя не найдено');
        return;
    }

    if (!phone) {
        alert('Ошибка: телефон пользователя не найден');
        return;
    }

    if (!address) {
        alert('Введите адрес');
        return;
    }

    if (!paymentMethod) {
        alert('Выберите способ оплаты');
        return;
    }

    const btn = e.target.querySelector('button[type="submit"]');
    btn.disabled = true;
    btn.textContent = 'Отправка...';

    try {
        const total = cart.reduce((sum, i) => sum + i.price * i.quantity, 0);
        const res = await sendWithAuth(`${API}/order`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: name,
                phone: phone,
                address: address,
                items: cart,
                total_price: total,
                payment_method_id: parseInt(paymentMethod)
            })
        });

        const result = await res.json();

        if (result.success) {
            currentOrder = {
                id: result.order_id,
                name: name,
                phone: phone,
                address: address,
                total: total
            };

            cart = [];
            updateCart();
            saveCart();
            closeCheckout();

            alert('Заказ успешно оформлен! Номер заказа: ' + result.order_id);
            showPage('history');
            loadHistory();
        } else {
            alert('Ошибка: ' + (result.error || 'Не удалось создать заказ'));
        }
    } catch (err) {
        alert('Ошибка отправки заказа');
        console.error(err);
    } finally {
        btn.disabled = false;
        btn.textContent = 'Подтвердить';
    }
}

//       ПРИ ЗАГРУЗКЕ СТРАНИЦЫ    

window.addEventListener('DOMContentLoaded', () => {
    // 1. Загружаем сохраненную сессию
    loadSession();

    // 2. Загружаем корзину
    loadCart();

    // 3. Обновляем интерфейс в зависимости от авторизации (ВАЖНО: до loadDrinks)
    updateAuthUI();

    // 4. Загружаем напитки
    loadDrinks();

    // 5. Обновляем отображение корзины
    updateCart();
});

// Закрытие модального окна при клике вне его
window.addEventListener('click', (e) => {
    if (e.target.id === 'checkoutModal') closeCheckout();
});