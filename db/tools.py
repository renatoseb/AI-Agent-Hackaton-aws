
def delete_tables(conn):
    with conn.cursor() as cur:
        cur.execute("DROP TABLE IF EXISTS tools;")
        conn.commit()

def create_tables(conn):
    with conn.cursor() as cur:
        cur.execute('''
            CREATE TABLE IF NOT EXISTS tools (
                id SERIAL PRIMARY KEY,
                toolname VARCHAR(50) NOT NULL,
                tooldescription VARCHAR(1000) NOT NULL
            );
        ''')
        conn.commit()

def insert_data(conn, tools):
    for tool in tools:
        with conn.cursor() as cur:
            cur.execute('''
                INSERT INTO tools (toolname, tooldescription)
                VALUES (%s, %s)
            ''', (tool['toolname'], tool['tooldescription']))
            conn.commit()

def get_all_tools(conn):
    with conn.cursor() as cur:
        cur.execute("SELECT toolname, tooldescription FROM tools;")
        return cur.fetchall()

if __name__ == '__main__':
    from conn import connect
    conn = connect()
    delete_tables(conn)
    
    tools = [
        {
            "toolname": "Productos_FDA",
            "tooldescription": '''"Activa si el usuario solicita información sobre alertas, reportes o retiros de productos registrados por la FDA (Food and Drug Administration).  \nKeywords: FDA, producto reportado, alerta sanitaria, retiro, advertencia, revisión FDA, producto prohibido, producto contaminado.  \n🚫 No confundir con: consultas sobre recetas o información nutricional."'''
        },
        {
            "toolname": "Recomendar_Receta",
            "tooldescription": '''"Activa si el usuario pide recomendaciones de recetas, comidas o ideas para preparar alimentos según sus preferencias o tipo de dieta.  \nKeywords: receta, recetas, comida, preparar, ideas, almuerzo, cena, desayuno, saludable, recomendación, sugerencia.  \n🚫 No confundir con: consultas sobre reportes FDA o información de un producto específico."'''
        },
        {
            "toolname": "Recomendar_Ingredientes",
            "tooldescription": '''"Activa si el usuario indica restricciones, alergias o ingredientes específicos y desea que se recomienden recetas o preparaciones adecuadas.  \nKeywords: sin gluten, sin azúcar, sin lactosa, alergia, intolerancia, vegetariano, vegano, sin carne, evitar, ingredientes permitidos.  \n🚫 No confundir con: búsquedas generales de recetas sin restricciones o verificaciones FDA."'''
        }
    ]
    create_tables(conn)
    insert_data(conn, tools)
    conn.close()