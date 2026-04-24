from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


# Связь "многие-ко-многим" между пользователями и купленными играми
user_games = db.Table(
    "user_games",
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
    db.Column("game_id", db.Integer, db.ForeignKey("games.id"), primary_key=True),
)


# Связь "многие-ко-многим" между пользователями и корзиной
cart_items = db.Table(
    "cart_items",
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), primary_key=True),
    db.Column("game_id", db.Integer, db.ForeignKey("games.id"), primary_key=True),
)


class Game(db.Model):
    __tablename__ = "games"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=False)
    image_url = db.Column(db.String(500), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    developer = db.Column(db.String(120), nullable=False)
    release_year = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f"<Game {self.id}: {self.name}>"


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)  # Хэш пароля
    email = db.Column(db.String(120), unique=True, nullable=False)
    avatar_url = db.Column(db.String(500), nullable=True)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    balance = db.Column(db.Float, default=0.0, nullable=False)

    purchased_games = db.relationship(
        "Game",
        secondary=user_games,
        lazy="subquery",
        backref=db.backref("owners", lazy=True),
    )
    cart_games = db.relationship(
        "Game",
        secondary=cart_items,
        lazy="subquery",
        backref=db.backref("in_carts", lazy=True),
    )

    def __repr__(self):
        return f"<User {self.id}: {self.username}>"
