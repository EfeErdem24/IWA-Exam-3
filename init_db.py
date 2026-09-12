import sqlite3
import os
from werkzeug.security import generate_password_hash

DATABASE = 'school.db'

def initDatabase() :
        if os.path.exists(DATABASE):
                os.remove(DATABASE)

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        cursor.execute("PRAGMA foreign_keys = ON;")

        # Initializing tables

        # Initializing simulation time
        cursor.execute("""
                                CREATE TABLE IF NOT EXISTS simulation (
                                        key TEXT PRIMARY KEY,
                                        value TEXT NOT NULL
                                );
                                """)
        
        cursor.execute("""
                                CREATE TABLE IF NOT EXISTS users (
                                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                                        first_name TEXT NOT NULL,
                                        last_name TEXT NOT NULL,
                                        email TEXT UNIQUE NOT NULL,
                                        password TEXT NOT NULL,
                                        role TEXT NOT NULL CHECK (role IN ('manager', 'student'))
                                );
                                """)

        cursor.execute("""
                                CREATE TABLE IF NOT EXISTS classes (
                                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                                        manager_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                                        title TEXT NOT NULL,
                                        cuisine TEXT NOT NULL, 
                                        difficulty TEXT NOT NULL,
                                        duration INTEGER NOT NULL,
                                        dietary_category TEXT NOT NULL CHECK(dietary_category IN ('Standard', 'Vegetarian', 'Vegan', 'Gluten-free')),
                                        chef TEXT NOT NULL,
                                        ingredients TEXT NOT NULL,
                                        description TEXT NOT NULL,
                                        photo1 TEXT NOT NULL,
                                        photo2 TEXT NOT NULL,
                                        photo3 TEXT NOT NULL
                                );
                                """)

        cursor.execute("""
                                CREATE TABLE IF NOT EXISTS sessions (
                                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                                        class_id INTEGER NOT NULL REFERENCES classes(id) ON DELETE CASCADE,
                                        day_of_week TEXT NOT NULL,
                                        day_order INTEGER NOT NULL,
                                        start_time TEXT NOT NULL,
                                        kitchen TEXT NOT NULL,
                                        capacity INTEGER NOT NULL CHECK(capacity > 0)
                                );
                                """)

        cursor.execute("""
                                CREATE TABLE IF NOT EXISTS enrollments (
                                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                                        session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                                        student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                                        enrolled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                        UNIQUE(session_id, student_id)
                                );
                                """)
        
        cursor.execute("""
                                CREATE TABLE IF NOT EXISTS ratings (
                                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                                        session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                                        student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                                        score INTEGER NOT NULL CHECK(score BETWEEN 1 AND 5),
                                        comment TEXT,
                                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                        UNIQUE(session_id, student_id)
                                );
                                """)

        cursor.execute("""
                                CREATE TABLE IF NOT EXISTS waiting_list (
                                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                                        session_id INTEGER NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                                        student_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                                        joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                        UNIQUE(session_id, student_id)
                                );
                                """)

        # Simulating time as Wednesday 14:00
        cursor.execute("INSERT INTO simulation (key, value) VALUES ('simulated_day', 'Wednesday');")
        cursor.execute("INSERT INTO simulation (key, value) VALUES ('simulated_time', '14:00');")

        # Simulating user data
        user_data = [
                ("Manager", "1", "manager1@email.com", generate_password_hash("manager1"), 'manager'),
                ("Manager", "2", "manager2@email.com", generate_password_hash("manager2"), 'manager'),
                ("Efe", "Erdem", "efe@email.com", generate_password_hash("Efe123"), 'student'),
                ("Student", "2", "student2@email.com", generate_password_hash("student2"), 'student'),
                ("Student", "3", "student3@email.com", generate_password_hash("student3"), 'student'),
                ("Student", "4", "student4@email.com", generate_password_hash("student4"), 'student'),
        ]

        cursor.executemany(
        "INSERT INTO users (first_name, last_name, email, password, role) VALUES (?, ?, ?, ?, ?);",
        user_data)

        # Simulating classes
        class_data = [
        (
            1, 
            "Authentic Neapolitan Pizza & Focaccia",
            "Italian",
            "Beginner",
            120,
            "Vegetarian",
            "Antonio Rossi",
            "Caputo '00' Flour\nSan Marzano DOP Tomatoes\nFresh Buffalo Mozzarella\nExtra Virgin Olive Oil\nFresh Basil Leaves",
            "Discover the authentic art of traditional Neapolitan pizza and Ligurian focaccia. Master high-hydration dough fermentation, hand-stretching, and wood-fire baking techniques.",
            "authentic-neapolitan-pizza-focaccia/pizza1.jpg", "authentic-neapolitan-pizza-focaccia/pizza2.jpg", "authentic-neapolitan-pizza-focaccia/pizza3.jpg"
        ),
        (
            1, 
            "Mastering Handmade Sushi & Sashimi",
            "Japanese",
            "Intermediate",
            150,
            "Gluten-free",
            "Kenji Sato",
            "Sushi-grade Atlantic Salmon\nJapanese Koshihikari Rice\nSeasoned Rice Vinegar\nNori Seaweed Sheets\nFresh Wasabi Root",
            "Learn precision knife techniques and Japanese culinary principles. Craft seasoned sushi rice, salmon and tuna nigiri, maki rolls, and delicate fresh sashimi cuts.",
            "mastering-handmade-sushi-sashimi/sushi1.jpg", "mastering-handmade-sushi-sashimi/sushi2.jpg", "mastering-handmade-sushi-sashimi/sushi3.jpg"
        ),
        (
            2, 
            "Classic French Pastry & Macarons",
            "French",
            "Advanced",
            180,
            "Vegetarian",
            "Helena Vidal",
            "Extra-Fine Almond Flour\nOrganic Egg Whites\nValrhona Dark Chocolate\nCultured French Butter\nTahitian Vanilla Pods",
            "Dive into elite French patisserie. Create flawless Parisian macarons with delicate shells, silky dark chocolate ganache, and seasonal fruit coulis.",
            "classic-french-pastry-macarons/pastry1.jpg", "classic-french-pastry-macarons/pastry2.jpg", "classic-french-pastry-macarons/pastry3.jpg"
        ),
        (
            2, 
            "Street Tacos & Fresh Guacamole Workshop",
            "Mexican",
            "Beginner",
            90,
            "Standard",
            "Carlos Mendez",
            "Nixtamalized Corn Masa Harina\nMarinated Skirt Steak (Carne Asada)\nRipe Haas Avocados\nFresh Limes & Cilantro\nCharred Tomatillos & Chipotle",
            "Vibrant street food flavors from scratch! Press fresh warm corn tortillas, sear tender carne asada, crush traditional molcajete guacamole, and balance homemade salsas.",
            "street-tacos-fresh-guacamole-workshop/tacos1.jpg", "street-tacos-fresh-guacamole-workshop/tacos2.jpg", "street-tacos-fresh-guacamole-workshop/tacos3.jpg"
        ),
        (
            1, 
            "Southeast Anatolian Alinazik ",
            "Turkish",
            "Advanced",
            240,
            "Standard",
            "İmam Çağdaş",
            "Eggplant (Aubergine)\nStrained Yogurt (Süzme Yoğurt)\nGarlic\nLamb Meat\nButter or Olive Oil\nSeasonings",
            "Master a Gaziantep classic from scratch. Char eggplants over an open flame to create a smoky garlic yogurt puree, sear tender spiced lamb, and finish with a sizzling red pepper butter drizzle.",
            "southeast-anatolian-alinazik/alinazik1.jpg", "southeast-anatolian-alinazik/alinazik2.jpg", "southeast-anatolian-alinazik/alinazik3.jpg"
        )
        ]

        cursor.executemany("""
        INSERT INTO classes (
            manager_id, title, cuisine, difficulty, duration,
            dietary_category, chef, ingredients, description,
            photo1, photo2, photo3
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,    
        class_data
        )

        # Inserting Schedule

        sessions_data = [
        # Past Sessions
        (1, "Monday", 1, "10:00", "Authentic Neapolitan Pizza & Focaccia 1", 4),
        (2, "Tuesday", 2, "18:00", "Mastering Handmade Sushi & Sashimi 1", 4),
        (4, "Wednesday", 3, "10:00", "Street Tacos & Fresh Guacamole Workshop 1", 4),
        # Upcoming Sessions
        (1, "Thursday", 4, "18:00", "Authentic Neapolitan Pizza & Focaccia 2", 3),
        (3, "Friday", 5, "15:00", "Classic French Pastry & Macarons 1", 4),
        (5, "Saturday", 6, "11:00", "Southeast Anatolian Alinazik 1", 4),
        (3, "Sunday", 7, "11:00", "Classic French Pastry & Macarons 2", 4),
        ]

        cursor.executemany(
        """
        INSERT INTO sessions (class_id, day_of_week, day_order, start_time, kitchen, capacity)
        VALUES (?, ?, ?, ?, ?, ?);
        """,
        sessions_data)

        enrollment_data = [
            # Past session enrollments:
            (1, 3), (1, 4),          
            (2, 3), (2, 5),          
            (3, 4), (3, 6),          
            # Fully booked session: Thursday Pizza (Session 4, capacity 3)
            (4, 4), (4, 5), (4, 6),  
            # Upcoming sessions:
            (5, 3), (5, 6),          
            (6, 4),                  
            
        ]

        cursor.executemany("""
        INSERT INTO enrollments (session_id, student_id)
        VALUES (?, ?);
        """, 
        enrollment_data)

        ratings_data = [
            (1, 3, 5, "Incredible pizza class! Dough fermentation tips were top notch."),
            (1, 4, 5, "Loved the crispy crust and fresh buffalo mozzarella."),
            (2, 3, 5, "Mastering salmon nigiri was so rewarding. Chef Kenji was patient and clear."),
            (2, 5, 4, "Great knife techniques learned, very fresh fish."),
            (3, 4, 4, "Delicious marinade and fresh corn tortillas made from scratch!"),
            (3, 6, 5, "Best tacos in town. Great atmosphere and delicious guacamole.")
        ]

        cursor.executemany("""
        INSERT INTO ratings (session_id, student_id, score, comment)
        VALUES (?, ?, ?, ?);
        """, 
        ratings_data)

        # Implementing waiting list
        cursor.execute("INSERT INTO waiting_list (session_id, student_id) VALUES (4, 3);")

        conn.commit()
        conn.close()
        print("Database 'school.db' successfully initialized.")

if __name__ == '__main__':
        initDatabase()


        

        