
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
            "tooldescription": '''"Activa si el usuario solicita recomendaciones generales de comidas o recetas **sin mencionar ingredientes específicos**, normalmente asociadas a momentos del día, tipos de comida o estilos de alimentación.  \nEj: 'recetas para desayuno', 'ideas de cena ligera', 'qué puedo cocinar hoy', 'comidas saludables para bajar de peso'.  \nKeywords: receta, recetas, comida, preparar, ideas, almuerzo, cena, desayuno, saludable, recomendación, sugerencia, menú, dieta.  \n🚫 No confundir con: solicitudes que incluyan ingredientes concretos o restricciones alimentarias (eso activa *Recomendar_Ingredientes*)."'''
        },
        {
            "toolname": "Recomendar_Ingredientes",
            "tooldescription": '''"Activa si el usuario menciona **ingredientes concretos** o establece **restricciones alimentarias** (por ejemplo, alergias o ingredientes a evitar) y desea que se sugieran recetas adecuadas.  \nEj: 'tengo pollo y arroz, qué puedo hacer', 'sin gluten y sin azúcar', 'recetas con atún y palta', 'comidas veganas sin carne'.  \nKeywords: con, sin, tengo, usar, incluir, evitar, sin gluten, sin azúcar, sin lactosa, alergia, intolerancia, vegetariano, vegano, ingredientes permitidos.  \n🚫 No confundir con: búsquedas generales de recetas sin ingredientes específicos o basadas en tipo de comida o horario (eso activa *Recomendar_Receta*)."'''
        }
    ]
    create_tables(conn)
    insert_data(conn, tools)
    conn.close()