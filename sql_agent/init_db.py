import sqlite3
import uuid

# Connect to SQLite database (creates file if it doesn't exist)
conn = sqlite3.connect('recipes.db')
cursor = conn.cursor()

# Create tables
cursor.execute('''
CREATE TABLE IF NOT EXISTS recipes (
    uid TEXT PRIMARY KEY,
    name TEXT NOT NULL
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS ingredients (
    uid TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    supply INTEGER NOT NULL
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS recipe_ingredient (
    recipe_uid TEXT,
    ingredient_uid TEXT,
    quantity INTEGER NOT NULL,
    FOREIGN KEY (recipe_uid) REFERENCES recipes(uid),
    FOREIGN KEY (ingredient_uid) REFERENCES ingredients(uid),
    PRIMARY KEY (recipe_uid, ingredient_uid)
)
''')

# Add ingredients
ingredients_data = [
    ('eggs', 10),
    ('milk', 2),
    ('tomato', 1),
    ('apple', 2),
    ('lemon', 3)
]

ingredient_uids = {}
for name, supply in ingredients_data:
    uid = str(uuid.uuid4())
    ingredient_uids[name] = uid
    cursor.execute('INSERT INTO ingredients (uid, name, supply) VALUES (?, ?, ?)',
                   (uid, name, supply))

# Add recipes
recipes_data = [
    ('lemon cake', [('eggs', 3), ('milk', 1), ('lemon', 3)]),
    ('apple cake', [('eggs', 3), ('milk', 1), ('apple', 2)]),
    ('scramble eggs', [('eggs', 5)])
]

for recipe_name, ingredients in recipes_data:
    recipe_uid = str(uuid.uuid4())
    cursor.execute('INSERT INTO recipes (uid, name) VALUES (?, ?)',
                   (recipe_uid, recipe_name))

    for ingredient_name, quantity in ingredients:
        cursor.execute('INSERT INTO recipe_ingredient (recipe_uid, ingredient_uid, quantity) VALUES (?, ?, ?)',
                       (recipe_uid, ingredient_uids[ingredient_name], quantity))

# Commit changes
conn.commit()

# Display the data to verify
print("=== INGREDIENTS ===")
cursor.execute('SELECT name, supply FROM ingredients')
for row in cursor.fetchall():
    print(f"{row[0]}: {row[1]}")

print("\n=== RECIPES ===")
cursor.execute('SELECT name FROM recipes')
for row in cursor.fetchall():
    print(row[0])

print("\n=== RECIPE DETAILS ===")
cursor.execute('''
SELECT r.name, i.name, ri.quantity
FROM recipes r
JOIN recipe_ingredient ri ON r.uid = ri.recipe_uid
JOIN ingredients i ON ri.ingredient_uid = i.uid
ORDER BY r.name, i.name
''')
for row in cursor.fetchall():
    print(f"{row[0]} -> {row[2]} {row[1]}")

# Close connection
conn.close()

print("\nDatabase 'recipes.db' created successfully!")