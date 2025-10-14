
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
            "toolname": "Paquete_Documentario",
            "tooldescription": '''"Activa si el usuario solicita su generación de boleta, factura, errores en la generación de facturas, montos de pedidos, paquete documentario, guía de pedido, resumen o PDF con el detalle de su compra (productos, importes, pagos), o quiere ver lo que le cobraron o cuánto pagó.  \nKeywords: boleta, factura, paquete, guía, resumen, PDF, lo que pagué, me cobraron, detalle de pago, ver lo pagado, detalle de cobro, productos cobrados, comprobante.  \n🚫 No confundir con: consulta de puntos, promociones de campaña, o fechas para pedir."'''
        },
        {
            "toolname": "Consultar_Deuda",
            "tooldescription": '''"Activa si quiere saber cuánto debe, si está al día, hasta cuándo puede pagar, o cuánto cupo disponible tiene.  \nKeywords: deuda, estado de cuenta, pagar, pago, fecha de pago, límite, cupo, crédito disponible.  \n🚫 No confundir con: fechas para pasar pedido, puntos, facturación, pagos, factura, últimos movimientos."'''
        },
        {
            "toolname": "Solicitar_L_nea_de_Cr_dito",
            "tooldescription": '''"Activa si quiere pedir una línea de crédito.  \nKeywords: solicitar, línea, crédito.  \n🚫 No confundir con: consultar deuda."'''
        },
        {
            "toolname": "_ltimos_Movimientos",
            "tooldescription": '''"Activa si pide ver sus pedidos pasados o últimos movimientos.  \nKeywords: últimos, movimientos, pedidos.  \n🚫 No confundir con: boleta, factura, paquete documentario, PDF del pedido, monto pagado, lo que me cobraron, ver lo que pagué, resumen de compra."'''
        },
        {
            "toolname": "Medios_de_Pago",
            "tooldescription": '''"Activa si pregunta cómo pagar. Muestra link de pago o bancos.  \nKeywords: medios, métodos, pagar.  \n🚫 No confundir con: consultar deuda."'''
        },
        {
            "toolname": "Fecha_de_Facturaci_n",
            "tooldescription": '''"Activa únicamente si pregunta cuándo se facturó su pedido en específico.  \nKeywords: fecha, facturación, pedido.  \n🚫 No confundir con: fechas para pasar pedido ni con fechas generales sin referenciar un pedido."'''
        },
        {
            "toolname": "SwitchTopic",
            "tooldescription": '''"Permite cambiar de tema. Agrupa flujos complejos (Mensajes No Deseados, Atención al Cliente, Entrenamiento, Menús Dinámicos, Preguntas Generales, Relacionado a Incentivos, Small Talk, Relacionado a Registro, Cuenta de Usuario, Documentos y Links, Relacionado a Pedidos, Relacionado a Productos, Testing Slots)."'''
        },
        {
            "toolname": "Belcorp___STSaludo",
            "tooldescription": '''"Activa cuando el usuario envía un saludo simple o un mensaje corto sin intención clara.  \nEj: 'hola', 'buenas', 'qué tal', 'hola Isa'.  \n🚫 No activar si el mensaje menciona 'asesor', 'ayuda', 'hablar con alguien' o 'soporte'."'''
        },
        {
            "toolname": "Belcorp___Answer_product_query",
            "tooldescription": '''"Activa si el usuario pregunta sobre un producto específico no cubierto por los flujos PREDT.  \nEj: ingredientes, uso, beneficios, recomendación según perfil.  \n🚫 No confundir con entrenamientos ni campañas específicas."'''
        },
        {
            "toolname": "Belcorp___Ofertas",
            "tooldescription": '''"Activa si pregunta por descuentos, promociones, packs o combos.  \nKeywords: descuentos, ofertas, promociones, packs, combos, kits, precio especial.  \n🚫 No confundir con fechas de campaña o uso de producto."'''
        },
        {
            "toolname": "Belcorp___code",
            "tooldescription": '''"Activa si quiere saber el código de un producto.  \nKeywords: código, producto."'''
        },
        {
            "toolname": "Belcorp___Add_product",
            "tooldescription": '''"Activa si quiere saber cómo agregar un producto a su pedido.  \nKeywords: agregar, producto, pedido."'''
        },
        {
            "toolname": "Belcorp___Asesor_de_bases",
            "tooldescription": '''"Activa si busca una base según su tono o tipo de piel.  \nKeywords: base, maquillaje, foundation, piel, tono, tipo de piel.  \n🚫 No confundir con la palabra 'asesor' sola."'''
        },
        {
            "toolname": "PREDT___Perfume_Larga_Duraci_n_Hombre",
            "tooldescription": '''"Activa si busca un perfume de larga duración para hombre.  \nKeywords: perfume, fragancia, larga duración, duradero, hombre.  \n🚫 No confundir con perfumes femeninos."'''
        },
        {
            "toolname": "PREDT___Punta_Delineador",
            "tooldescription": '''"Activa si pregunta cómo sacar punta al delineador.  \nKeywords: punta, sacar, tajar, delineador."'''
        },
        {
            "toolname": "PREDT___Base_Piel_Grasa",
            "tooldescription": '''"Activa si busca recomendaciones o pregunta sobre 'base para piel grasa'.  \nKeywords: base, piel, grasa."'''
        },
        {
            "toolname": "PREDT___Perfume_Fuerte",
            "tooldescription": '''"Activa si busca perfume fuerte.  \nKeywords: perfume, fuerte.  \n🚫 No confundir con perfume delicado."'''
        },
        {
            "toolname": "PREDT___Perfume_Delicado",
            "tooldescription": '''"Activa si busca perfume delicado o de aroma suave para mujer (Mythika, Miss, Fleur).  \nKeywords: perfume delicado, aroma suave, fragancia ligera, Mythika, Miss, Fleur.  \n🚫 No confundir con perfume para hombre."'''

        },
        {
            "toolname": "ClarifyFromUser",
            "tooldescription": '''"Activa cuando se requiere pedir aclaración al usuario si su mensaje no permite determinar con certeza qué herramienta usar."'''
        }
    ]
    create_tables(conn)
    insert_data(conn, tools)
    conn.close()