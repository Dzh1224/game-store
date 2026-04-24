import random
from urllib.parse import quote_plus

from sqlalchemy import text
from werkzeug.security import generate_password_hash

from models import Game, User, db


def _generate_description(game_name, category, developer, year):
    # Делаем расширенное описание 100-300 символов
    text = (
        f"{game_name} — популярная игра в жанре {category} от студии {developer}, "
        f"выпущенная в {year} году. В проекте сочетаются динамичный геймплей, "
        "интересная система прогрессии, качественная постановка и высокий уровень "
        "реиграбельности. Игра подойдет как новичкам, так и опытным игрокам, "
        "которые ценят насыщенный контент и атмосферу."
    )
    return text[:280]


def _get_popular_games_catalog():
    # База популярных реальных игр (будет расширена до 120 позиций с разными изданиями)
    return [
        ("The Witcher 3: Wild Hunt", "RPG", "CD Projekt RED", 2015),
        ("Cyberpunk 2077", "RPG", "CD Projekt RED", 2020),
        ("Elden Ring", "RPG", "FromSoftware", 2022),
        ("Baldur's Gate 3", "RPG", "Larian Studios", 2023),
        ("Skyrim", "RPG", "Bethesda Game Studios", 2011),
        ("Dark Souls III", "RPG", "FromSoftware", 2016),
        ("Divinity: Original Sin 2", "RPG", "Larian Studios", 2017),
        ("Diablo IV", "RPG", "Blizzard Entertainment", 2023),
        ("Red Dead Redemption 2", "Action", "Rockstar Games", 2018),
        ("Grand Theft Auto V", "Action", "Rockstar Games", 2013),
        ("DOOM Eternal", "Action", "id Software", 2020),
        ("Sekiro: Shadows Die Twice", "Action", "FromSoftware", 2019),
        ("Hades", "Action", "Supergiant Games", 2020),
        ("God of War", "Action", "Santa Monica Studio", 2018),
        ("Ghost of Tsushima", "Action", "Sucker Punch Productions", 2020),
        ("Helldivers 2", "Action", "Arrowhead Game Studios", 2024),
        ("Civilization VI", "Strategy", "Firaxis Games", 2016),
        ("Total War: WARHAMMER III", "Strategy", "Creative Assembly", 2022),
        ("Age of Empires IV", "Strategy", "Relic Entertainment", 2021),
        ("Crusader Kings III", "Strategy", "Paradox Development Studio", 2020),
        ("XCOM 2", "Strategy", "Firaxis Games", 2016),
        ("Stellaris", "Strategy", "Paradox Development Studio", 2016),
        ("Hearts of Iron IV", "Strategy", "Paradox Development Studio", 2016),
        ("Company of Heroes 3", "Strategy", "Relic Entertainment", 2023),
        ("Minecraft", "Indie", "Mojang Studios", 2011),
        ("Terraria", "Indie", "Re-Logic", 2011),
        ("Stardew Valley", "Indie", "ConcernedApe", 2016),
        ("Hollow Knight", "Indie", "Team Cherry", 2017),
        ("Celeste", "Indie", "Maddy Makes Games", 2018),
        ("Undertale", "Indie", "tobyfox", 2015),
        ("Dead Cells", "Indie", "Motion Twin", 2018),
        ("Slay the Spire", "Indie", "Mega Crit", 2019),
        ("The Last of Us Part I", "Adventure", "Naughty Dog", 2022),
        ("Uncharted 4: A Thief's End", "Adventure", "Naughty Dog", 2016),
        ("A Plague Tale: Requiem", "Adventure", "Asobo Studio", 2022),
        ("Detroit: Become Human", "Adventure", "Quantic Dream", 2018),
        ("Death Stranding", "Adventure", "Kojima Productions", 2019),
        ("Firewatch", "Adventure", "Campo Santo", 2016),
        ("Life is Strange", "Adventure", "Dontnod Entertainment", 2015),
        ("Subnautica", "Adventure", "Unknown Worlds Entertainment", 2018),
        ("Portal 2", "Adventure", "Valve", 2011),
        ("Resident Evil 4", "Horror", "Capcom", 2023),
        ("Silent Hill 2", "Horror", "Bloober Team", 2024),
        ("Dead Space", "Horror", "Motive Studio", 2023),
        ("Outlast", "Horror", "Red Barrels", 2013),
        ("The Forest", "Horror", "Endnight Games", 2018),
        ("EA Sports FC 25", "Sports", "EA Vancouver", 2024),
        ("NBA 2K25", "Sports", "Visual Concepts", 2024),
        ("F1 24", "Sports", "Codemasters", 2024),
        ("Forza Horizon 5", "Sports", "Playground Games", 2021),
        ("Gran Turismo 7", "Sports", "Polyphony Digital", 2022),
        ("Microsoft Flight Simulator", "Simulator", "Asobo Studio", 2020),
        ("Euro Truck Simulator 2", "Simulator", "SCS Software", 2012),
        ("The Sims 4", "Simulator", "Maxis", 2014),
        ("Cities: Skylines II", "Simulator", "Colossal Order", 2023),
    ]


def _seed_games():
    base_games = _get_popular_games_catalog()
    editions = ["Standard Edition", "Deluxe Edition", "Ultimate Edition"]
    random.seed(42)
    games = []
    for title, category, developer, year in base_games:
        for edition in editions:
            full_title = f"{title} ({edition})"
            # Цены в рублях
            price = float(random.randint(399, 4999))
            description = _generate_description(full_title, category, developer, year)
            image_url = f"https://placehold.co/400x250?text={quote_plus(full_title)}"
            games.append(
                Game(
                    name=full_title,
                    price=price,
                    description=description,
                    image_url=image_url,
                    category=category,
                    developer=developer,
                    release_year=year,
                )
            )

    # На случай изменения набора: добиваем до 120+ записей
    while len(games) < 120:
        title, category, developer, year = random.choice(base_games)
        suffix = random.randint(1, 99)
        full_title = f"{title} (Collector's Pack {suffix})"
        price = float(random.randint(399, 4999))
        description = _generate_description(full_title, category, developer, year)
        image_url = f"https://placehold.co/400x250?text={quote_plus(title)}"
        games.append(
            Game(
                name=full_title,
                price=price,
                description=description,
                image_url=image_url,
                category=category,
                developer=developer,
                release_year=year,
            )
        )
    db.session.add_all(games)


def _replace_catalog_if_needed():
    # Если каталог старый или в нем нет новых популярных игр, пересоздаем его
    has_any_standard = Game.query.filter(Game.name.like("%(Standard Edition)%")).first() is not None
    has_new_game = Game.query.filter(Game.name.like("Portal 2 (Standard Edition)")).first() is not None
    if has_any_standard and has_new_game:
        return

    users = User.query.all()
    for user in users:
        user.purchased_games.clear()
        user.cart_games.clear()
    db.session.flush()

    for game in Game.query.all():
        db.session.delete(game)
    db.session.flush()

    _seed_games()


def init_db(app):
    # Инициализация SQLAlchemy и первичное заполнение данных
    db.init_app(app)
    with app.app_context():
        db.create_all()
        user_columns = db.session.execute(text("PRAGMA table_info(users)")).fetchall()
        user_column_names = {column[1] for column in user_columns}
        if "avatar_url" not in user_column_names:
            db.session.execute(text("ALTER TABLE users ADD COLUMN avatar_url VARCHAR(500)"))
            db.session.commit()

        if not User.query.filter_by(username="admin").first():
            admin = User(
                username="admin",
                email="admin@gamestore.local",
                password=generate_password_hash("admin123456"),
                avatar_url=None,
                is_admin=True,
                balance=50000.0,
            )
            db.session.add(admin)

        if Game.query.count() < 100:
            _seed_games()
        else:
            _replace_catalog_if_needed()

        db.session.commit()
