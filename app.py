import os
import re
import uuid
from datetime import timedelta
from functools import wraps

from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_login import (
    LoginManager,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from database import init_db
from models import Game, User, db


app = Flask(__name__)
app.config["SECRET_KEY"] = "hexlet-game-store-secret-key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///game_store.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["REMEMBER_COOKIE_DURATION"] = timedelta(days=30)
app.config["GAME_IMAGES_FOLDER"] = os.path.join(app.static_folder, "images", "games")
app.config["ALLOWED_IMAGE_EXTENSIONS"] = {"png", "jpg", "jpeg", "webp", "gif"}

init_db(app)

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.login_message = "Please sign in first."
login_manager.init_app(app)


TRANSLATIONS = {
    "ru": {
        "store_name": "Game Store Hexlet",
        "catalog": "Каталог",
        "cart": "Корзина",
        "profile": "Профиль",
        "admin_panel": "Админка",
        "login": "Вход",
        "register": "Регистрация",
        "logout": "Выход",
        "balance": "Баланс",
        "theme": "Тема",
        "language": "Язык",
        "light": "Светлая",
        "dark": "Темная",
        "russian": "Русский",
        "english": "English",
        "game_catalog": "Каталог игр",
        "total": "Всего",
        "apply": "Применить",
        "reset": "Сбросить",
        "details": "Подробнее",
        "buy": "Купить",
        "already_owned": "Уже куплена",
        "not_enough_funds": "Недостаточно средств",
        "add_to_cart": "В корзину",
        "cart_title": "Корзина",
        "added_games": "Добавлено игр",
        "total_price": "Общий ценник",
        "selected": "Выбрано",
        "game": "Игра",
        "price": "Цена",
        "action": "Действие",
        "remove": "Удалить",
        "buy_selected": "Купить выбранные",
        "buy_all": "Купить всё",
        "cart_empty": "Корзина пустая.",
        "profile_title": "Личный кабинет",
        "purchased_games": "Купленные игры",
    },
    "en": {
        "store_name": "Game Store Hexlet",
        "catalog": "Catalog",
        "cart": "Cart",
        "profile": "Profile",
        "admin_panel": "Admin",
        "login": "Login",
        "register": "Register",
        "logout": "Logout",
        "balance": "Balance",
        "theme": "Theme",
        "language": "Language",
        "light": "Light",
        "dark": "Dark",
        "russian": "Russian",
        "english": "English",
        "game_catalog": "Game Catalog",
        "total": "Total",
        "apply": "Apply",
        "reset": "Reset",
        "details": "Details",
        "buy": "Buy",
        "already_owned": "Owned",
        "not_enough_funds": "Not enough funds",
        "add_to_cart": "Add to cart",
        "cart_title": "Cart",
        "added_games": "Games added",
        "total_price": "Total price",
        "selected": "Selected",
        "game": "Game",
        "price": "Price",
        "action": "Action",
        "remove": "Remove",
        "buy_selected": "Buy selected",
        "buy_all": "Buy all",
        "cart_empty": "Cart is empty.",
        "profile_title": "Profile",
        "purchased_games": "Purchased games",
    },
}


@app.before_request
def set_defaults():
    if session.get("theme") not in {"light", "dark"}:
        session["theme"] = "light"
    if session.get("lang") not in {"ru", "en"}:
        session["lang"] = "ru"


@app.context_processor
def inject_ui_settings():
    lang = session.get("lang", "ru")
    theme = session.get("theme", "light")
    messages = TRANSLATIONS.get(lang, TRANSLATIONS["ru"])

    def t(key):
        return messages.get(key, key)

    return {"t": t, "current_lang": lang, "current_theme": theme}


@app.route("/set-theme/<string:theme>")
def set_theme(theme):
    if theme in {"light", "dark"}:
        session["theme"] = theme
    return redirect(request.referrer or url_for("index"))


@app.route("/set-language/<string:lang>")
def set_language(lang):
    if lang in {"ru", "en"}:
        session["lang"] = lang
    return redirect(request.referrer or url_for("index"))


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def is_valid_email(email):
    # Простая проверка корректности email
    pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    return bool(re.match(pattern, email))


def save_game_image(image_file):
    if not image_file or not image_file.filename:
        return None, None

    original_name = secure_filename(image_file.filename)
    if "." not in original_name:
        return None, "Image must have file extension."

    extension = original_name.rsplit(".", 1)[1].lower()
    if extension not in app.config["ALLOWED_IMAGE_EXTENSIONS"]:
        return None, "Allowed image formats: png, jpg, jpeg, webp, gif."

    os.makedirs(app.config["GAME_IMAGES_FOLDER"], exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}.{extension}"
    file_path = os.path.join(app.config["GAME_IMAGES_FOLDER"], stored_name)
    image_file.save(file_path)
    return f"/static/images/games/{stored_name}", None


def admin_required(func):
    @wraps(func)
    @login_required
    def wrapper(*args, **kwargs):
        if not current_user.is_admin:
            flash("Access denied.", "danger")
            return redirect(url_for("index"))
        return func(*args, **kwargs)

    return wrapper


@app.route("/")
def index():
    page = request.args.get("page", 1, type=int)
    search = request.args.get("search", "", type=str).strip()
    category = request.args.get("category", "", type=str).strip()
    min_price = request.args.get("min_price", "", type=str).strip()
    max_price = request.args.get("max_price", "", type=str).strip()
    sort = request.args.get("sort", "id_asc", type=str).strip()

    # Базовый запрос каталога
    query = Game.query

    # Поиск по названию и разработчику
    if search:
        search_like = f"%{search}%"
        query = query.filter((Game.name.ilike(search_like)) | (Game.developer.ilike(search_like)))

    # Фильтр по категории
    if category:
        query = query.filter(Game.category == category)

    # Фильтр по минимальной цене
    if min_price:
        try:
            min_price_value = float(min_price)
            query = query.filter(Game.price >= min_price_value)
        except ValueError:
            flash("Минимальная цена указана некорректно.", "warning")

    # Фильтр по максимальной цене
    if max_price:
        try:
            max_price_value = float(max_price)
            query = query.filter(Game.price <= max_price_value)
        except ValueError:
            flash("Максимальная цена указана некорректно.", "warning")

    # Сортировка каталога
    sort_options = {
        "id_asc": Game.id.asc(),
        "id_desc": Game.id.desc(),
        "price_asc": Game.price.asc(),
        "price_desc": Game.price.desc(),
        "name_asc": Game.name.asc(),
        "name_desc": Game.name.desc(),
        "year_desc": Game.release_year.desc(),
        "year_asc": Game.release_year.asc(),
    }
    if sort not in sort_options:
        sort = "id_asc"
    query = query.order_by(sort_options[sort])

    games = query.paginate(page=page, per_page=20, error_out=False)
    categories = ["RPG", "Action", "Strategy", "Indie", "Adventure", "Simulator", "Sports", "Horror"]
    filters = {
        "search": search,
        "category": category,
        "min_price": min_price,
        "max_price": max_price,
        "sort": sort,
    }
    return render_template("index.html", games=games, categories=categories, filters=filters)


@app.route("/game/<int:game_id>")
def game_detail(game_id):
    game = Game.query.get_or_404(game_id)
    owned = current_user.is_authenticated and game in current_user.purchased_games
    in_cart = current_user.is_authenticated and game in current_user.cart_games
    return render_template("game_detail.html", game=game, owned=owned, in_cart=in_cart)


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if len(password) < 6:
            flash("Password must be at least 6 characters.", "danger")
            return redirect(url_for("register"))
        if not is_valid_email(email):
            flash("Please enter a valid email.", "danger")
            return redirect(url_for("register"))
        if User.query.filter_by(username=username).first():
            flash("Username is already taken.", "danger")
            return redirect(url_for("register"))
        if User.query.filter_by(email=email).first():
            flash("Email is already used.", "danger")
            return redirect(url_for("register"))

        user = User(
            username=username,
            email=email,
            password=generate_password_hash(password),
            is_admin=False,
            balance=0.0,
        )
        db.session.add(user)
        db.session.commit()
        flash("Registration successful. You can login now.", "success")
        return redirect(url_for("login"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        remember = bool(request.form.get("remember"))
        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            # Запоминаем сессию пользователя, если отмечен чекбокс "Запомнить меня"
            login_user(user, remember=remember)
            flash("Welcome back!", "success")
            return redirect(url_for("index"))

        flash("Invalid username or password.", "danger")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You are logged out.", "info")
    return redirect(url_for("index"))


@app.route("/profile")
@login_required
def profile():
    return render_template("profile.html")


@app.route("/topup", methods=["POST"])
@login_required
def topup():
    amount = request.form.get("amount", "0")
    try:
        amount_value = float(amount)
    except ValueError:
        flash("Invalid amount.", "danger")
        return redirect(url_for("profile"))

    if amount_value <= 0:
        flash("Amount must be greater than 0.", "danger")
        return redirect(url_for("profile"))

    current_user.balance += amount_value
    db.session.commit()
    flash(f"Баланс пополнен на {amount_value:.2f} ₽.", "success")
    return redirect(url_for("profile"))


@app.route("/cart")
@login_required
def cart():
    total = sum(game.price for game in current_user.cart_games)
    items_count = len(current_user.cart_games)
    return render_template("cart.html", total=total, items_count=items_count)


@app.route("/cart/add/<int:game_id>", methods=["POST"])
@login_required
def add_to_cart(game_id):
    game = Game.query.get_or_404(game_id)
    if game in current_user.purchased_games:
        flash("You already own this game.", "warning")
    elif game in current_user.cart_games:
        flash("Game already in cart.", "info")
    else:
        current_user.cart_games.append(game)
        db.session.commit()
        flash("Game added to cart.", "success")
    return redirect(request.referrer or url_for("index"))


@app.route("/cart/remove/<int:game_id>", methods=["POST"])
@login_required
def remove_from_cart(game_id):
    game = Game.query.get_or_404(game_id)
    if game in current_user.cart_games:
        current_user.cart_games.remove(game)
        db.session.commit()
        flash("Game removed from cart.", "info")
    return redirect(url_for("cart"))


@app.route("/cart/checkout", methods=["POST"])
@login_required
def checkout():
    if not current_user.cart_games:
        flash("Your cart is empty.", "warning")
        return redirect(url_for("cart"))

    total = sum(game.price for game in current_user.cart_games)
    if current_user.balance < total:
        flash("Not enough balance for checkout.", "danger")
        return redirect(url_for("cart"))

    current_user.balance -= total
    for game in list(current_user.cart_games):
        if game not in current_user.purchased_games:
            current_user.purchased_games.append(game)
        current_user.cart_games.remove(game)
    db.session.commit()
    flash("Purchase completed successfully.", "success")
    return redirect(url_for("profile"))


@app.route("/cart/checkout-selected", methods=["POST"])
@login_required
def checkout_selected():
    selected_ids_raw = request.form.getlist("selected_games")
    if not selected_ids_raw:
        flash("Выберите хотя бы одну игру для покупки.", "warning")
        return redirect(url_for("cart"))

    try:
        selected_ids = {int(game_id) for game_id in selected_ids_raw}
    except ValueError:
        flash("Некорректный набор игр.", "danger")
        return redirect(url_for("cart"))

    cart_games_by_id = {game.id: game for game in current_user.cart_games}
    selected_games = [cart_games_by_id[game_id] for game_id in selected_ids if game_id in cart_games_by_id]

    if not selected_games:
        flash("Выбранные игры не найдены в корзине.", "warning")
        return redirect(url_for("cart"))

    selected_total = sum(game.price for game in selected_games)
    if current_user.balance < selected_total:
        flash("Недостаточно средств для покупки выбранных игр.", "danger")
        return redirect(url_for("cart"))

    current_user.balance -= selected_total
    for game in selected_games:
        if game not in current_user.purchased_games:
            current_user.purchased_games.append(game)
        if game in current_user.cart_games:
            current_user.cart_games.remove(game)
    db.session.commit()
    flash("Выбранные игры успешно куплены.", "success")
    return redirect(url_for("profile"))


@app.route("/buy/<int:game_id>", methods=["POST"])
@login_required
def buy_game(game_id):
    game = Game.query.get_or_404(game_id)
    if game in current_user.purchased_games:
        flash("You already own this game.", "warning")
        return redirect(request.referrer or url_for("index"))

    if current_user.balance < game.price:
        flash("Not enough balance.", "danger")
        return redirect(request.referrer or url_for("index"))

    current_user.balance -= game.price
    current_user.purchased_games.append(game)
    if game in current_user.cart_games:
        current_user.cart_games.remove(game)
    db.session.commit()
    flash(f"You bought {game.name}.", "success")
    return redirect(url_for("profile"))


@app.route("/admin")
@admin_required
def admin():
    games = Game.query.order_by(Game.id.desc()).all()
    users = User.query.order_by(User.id.asc()).all()
    return render_template("admin.html", games=games, users=users)


@app.route("/admin/users/<int:user_id>")
@admin_required
def admin_user_profile(user_id):
    # Профиль пользователя для администратора с купленными играми
    user = User.query.get_or_404(user_id)
    return render_template("admin_user_profile.html", user=user)


@app.route("/admin/users/<int:user_id>/topup", methods=["POST"])
@admin_required
def admin_topup_user(user_id):
    # Админ может пополнять баланс себе и любому пользователю
    user = User.query.get_or_404(user_id)
    amount = request.form.get("amount", "0").strip()
    try:
        amount_value = float(amount)
    except ValueError:
        flash("Некорректная сумма пополнения.", "danger")
        return redirect(request.referrer or url_for("admin"))

    if amount_value <= 0:
        flash("Сумма должна быть больше 0.", "danger")
        return redirect(request.referrer or url_for("admin"))

    user.balance += amount_value
    db.session.commit()
    flash(f"Баланс пользователя {user.username} пополнен на {amount_value:.2f} ₽.", "success")
    return redirect(request.referrer or url_for("admin"))


@app.route("/admin/games/add", methods=["GET", "POST"])
@admin_required
def admin_add_game():
    if request.method == "POST":
        try:
            price = float(request.form.get("price", "0"))
            release_year = int(request.form.get("release_year", "2000"))
        except ValueError:
            flash("Price and year must be numeric.", "danger")
            return redirect(url_for("admin_add_game"))

        description = request.form.get("description", "").strip()
        if len(description) < 100:
            flash("Description must be at least 100 characters.", "danger")
            return redirect(url_for("admin_add_game"))

        uploaded_image_url, upload_error = save_game_image(request.files.get("image_file"))
        if upload_error:
            flash(upload_error, "danger")
            return redirect(url_for("admin_add_game"))

        image_url = uploaded_image_url or request.form.get("image_url", "").strip()
        if not image_url:
            flash("Provide image URL or upload image file.", "danger")
            return redirect(url_for("admin_add_game"))

        game = Game(
            name=request.form.get("name", "").strip(),
            price=price,
            description=description,
            image_url=image_url,
            category=request.form.get("category", "").strip(),
            developer=request.form.get("developer", "").strip(),
            release_year=release_year,
        )
        db.session.add(game)
        db.session.commit()
        flash("Game added.", "success")
        return redirect(url_for("admin"))
    return render_template("admin_add_game.html")


@app.route("/admin/games/edit/<int:game_id>", methods=["GET", "POST"])
@admin_required
def admin_edit_game(game_id):
    game = Game.query.get_or_404(game_id)
    if request.method == "POST":
        try:
            game.price = float(request.form.get("price", "0"))
            game.release_year = int(request.form.get("release_year", "2000"))
        except ValueError:
            flash("Price and year must be numeric.", "danger")
            return redirect(url_for("admin_edit_game", game_id=game_id))

        description = request.form.get("description", "").strip()
        if len(description) < 100:
            flash("Description must be at least 100 characters.", "danger")
            return redirect(url_for("admin_edit_game", game_id=game_id))

        uploaded_image_url, upload_error = save_game_image(request.files.get("image_file"))
        if upload_error:
            flash(upload_error, "danger")
            return redirect(url_for("admin_edit_game", game_id=game_id))

        game.name = request.form.get("name", "").strip()
        game.description = description
        form_image_url = request.form.get("image_url", "").strip()
        game.image_url = uploaded_image_url or form_image_url or game.image_url
        game.category = request.form.get("category", "").strip()
        game.developer = request.form.get("developer", "").strip()

        db.session.commit()
        flash("Game updated.", "success")
        return redirect(url_for("admin"))

    return render_template("admin_edit_game.html", game=game)


@app.route("/admin/games/delete/<int:game_id>", methods=["POST"])
@admin_required
def admin_delete_game(game_id):
    game = Game.query.get_or_404(game_id)
    db.session.delete(game)
    db.session.commit()
    flash("Game deleted.", "info")
    return redirect(url_for("admin"))


if __name__ == "__main__":
    app.run(debug=True, port=5000)
