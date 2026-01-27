import sqlite3
db_path = r"/Users/thomaszilliox/Documents/git_repos/local_ai_agent/sql_agent/recipes.db"

def query_database(query: str) -> str:
    """Execute a SQL query on the recipes database and return results."""
    try:
        print(f"Agent ask {query}")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        column_names = [description[0] for description in cursor.description]
        conn.close()

        if not results:
            return "No results found."

        # Format results as a readable string
        formatted_results = []
        for row in results:
            row_dict = dict(zip(column_names, row))
            formatted_results.append(str(row_dict))

        return "\n".join(formatted_results)
    except Exception as e:
        return f"Error executing query: {str(e)}"

if __name__ == "__main__":
    query = "SELECT name FROM recipes"
    print(query_database(query))