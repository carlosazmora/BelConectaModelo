import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import sqlite3
import requests

nombreAsesora = 'Sofía'
numeroTelefono = '+573004222046'

def simularBaseDatos():
    products = pd.read_json('products.json')

    # Conectar o crear la base de datos SQLite
    conn = sqlite3.connect('base.db')

    # Exportar el DataFrame a una tabla SQLite llamada 'products'
    products.to_sql('base', conn, if_exists='replace', index=False)

    # Crear la tabla de Clientes con datos ficticios
    clientes_data = pd.DataFrame({
        'id': [1, 2],
        'nombre': ['Ana', 'María']
    })
    clientes_data.to_sql('Clientes', conn, if_exists='replace', index=False)

    # Crear la tabla de Compras que relaciona Clientes y Productos
    compras_data = pd.DataFrame({
        'cliente_id': [1, 1, 1, 1, 1, 2, 2, 2, 2, 2],
        'codsap': ['200098377', '200092025', '200110157', '200113891', '200099047', '200111234', '200107850', '200087691', '200099047', '200102089']  
        # Ana - Fragancias, Luis - Tratamiento Corporal en su mayoría
    })
    compras_data.to_sql('compras', conn, if_exists='replace', index=False)

    # Cerrar la conexión
    conn.close()

    print("Los datos de 'products.json' se han migrado a la base de datos 'products.db' correctamente.")

def suggestionsToUser(nombreCliente):
    db_path = 'products.db'
    
    # Conectar a la base de datos SQLite
    conn = sqlite3.connect(db_path)
    
    # Leer los datos de la tabla 'products' y 'Clientes' desde la base de datos
    products = pd.read_sql_query("SELECT * FROM products", conn)
    clientes = pd.read_sql_query("SELECT * FROM Clientes WHERE nombre = ?", conn, params=(nombreCliente,))
    
    # Cerrar la conexión a la base de datos
    conn.close()
    
    if clientes.empty:
        print("No se encontró el cliente con ese nombre.")
        return []

    # Obtener el ID del cliente
    idCliente = int(clientes.iloc[0]['id'])
    
    # Leer los datos de compras para el cliente específico
    conn = sqlite3.connect(db_path)
    compras = pd.read_sql_query("SELECT * FROM compras WHERE cliente_id = ?", conn, params=(idCliente,))
 
    # Cerrar la conexión a la base de datos
    conn.close()
    
    # Obtener los IDs de los productos en compras
    compras_ids = compras['codsap'].astype(str).tolist()  # Asegurarse de que los IDs sean cadenas de texto
    
    # Filtrar los productos en products que tengan un ID presente en compras
    products_bought = products[products['codsap'].astype(str).isin(compras_ids)]

    if products_bought.empty:
        print("No se encontraron productos comprados para el cliente.")
        return []

    # Crear una lista para almacenar las descripciones por separado
    input_texts = []
    for _, row in products_bought.iterrows():
        # Combinar descategoria, desunidadnegocio y desmarca
        input_texts.append(" ".join([str(row['descategoria']), str(row['desunidadnegocio']), str(row['desmarca'])]))

    # Filtrar los productos en products que no tengan un ID presente en compras
    products_filtered = products[~products['codsap'].astype(str).isin(compras_ids)]

    if products_filtered.empty:
        print("No hay productos disponibles para sugerir.")
        return []

    # Vectorización y cálculo de similitud con products filtrados
    vectorizer = TfidfVectorizer()
    
    # Vectorizar los textos de los productos comprados y filtrados
    product_descriptions = products_filtered.apply(lambda row: " ".join([str(row[col]) for col in products_filtered.columns if col.startswith("des") and col not in ["desproducto"]]), axis=1)
    vectors = vectorizer.fit_transform(input_texts + product_descriptions.tolist())
    
    # Calcular similitudes
    cosine_similarities = cosine_similarity(vectors[:len(input_texts)], vectors[len(input_texts):]).flatten()
    
    # Sugerir las 5 mejores coincidencias
    top_1_indices = cosine_similarities.argsort()[::-1][:3]  # Obtener la mejor coincidencia
    
    # Asegurarse de que top_1_indices no exceda la longitud de products_filtered
    top_1_indices = top_1_indices[top_1_indices < len(products_filtered)]

    # Sugerir los productos
    sugerencias = products_filtered.iloc[top_1_indices]

    # Convertir las sugerencias a formato JSON y imprimirlas
    sugerencias_json = sugerencias.to_json(orient='records', indent=4)
    print(sugerencias_json)

    enviar(nombreCliente, sugerencias_json, products_bought)

def enviar(nombreCliente, sugerencias_json, products_bought):
    # URL de tu servidor Node.js (usa tu dirección de ngrok si estás desarrollando localmente)
    url = 'https://1cc9-201-221-122-178.ngrok-free.app/process-message'  # Reemplaza con tu URL de ngrok

    # Datos a enviar al servidor Node.js
    payload = {
        'message': 'Nuestro sistema detectó que' + nombreCliente +
        ' la cual ha comprado los siguientes productos:\n' + products_bought.to_string(index=False) + 
        '\n\nle puede gustar el siguiente producto:\n' + sugerencias_json +
        '\n\nDebes generar un mensaje de menos de 100 palabras informando a la asesora encargada, llamada ' + nombreAsesora + 
        ' sobre esta oportunidad.',
        'phoneNumber': 'whatsapp:' + numeroTelefono
    }

    # Enviar solicitud POST
    response = requests.post(url, json=payload)

    # Imprimir la respuesta
    if response.status_code == 200:
        print('Mensaje enviado con éxito:', response.json())
    else:
        print('Error al enviar el mensaje:', response.status_code, response.text)

def nuevaCampaña(numero):
    # URL de tu servidor Node.js (usa tu dirección de ngrok si estás desarrollando localmente)
    url = 'https://1cc9-201-221-122-178.ngrok-free.app/process-message'  # Reemplaza con tu URL de ngrok

    # Datos a enviar al servidor Node.js
    payload = {
        'message': 'La campaña número ' + numero + 
        ' ha sido lanzada. Tienes que informarle a la asesora' + nombreAsesora +
        'sobre este inicio, y recuerdale que revise el nuevo catálogo, no se te olvide desearle buena suerte. Haz que el mensaje no se pase de 100 palabras',
        'phoneNumber': 'whatsapp:' + numeroTelefono
    }

    # Enviar solicitud POST
    response = requests.post(url, json=payload)

    # Imprimir la respuesta
    if response.status_code == 200:
        print('Mensaje enviado con éxito:', response.json())
    else:
        print('Error al enviar el mensaje:', response.status_code, response.text)
    

def main():
    simularBaseDatos()

    while True:
        print("\n--- Menú de Gestión ---")
        print("1. Obtener Sugerencias para un Cliente")
        print("2. Crear Nueva Campaña")
        print("3. Salir")
        
        choice = input("Seleccione una opción (1/2/3): ")
        
        if choice == '1':
            cliente = input("Ingrese el nombre del cliente: ")
            suggestionsToUser(cliente)
            break
        elif choice == '2':
            campaña_id = input("Ingrese el ID de la nueva campaña: ")
            nuevaCampaña(campaña_id)
            break
        elif choice == '3':
            print("Saliendo del programa.")
            break
        else:
            print("Opción inválida. Por favor, intente de nuevo.")

if __name__ == "__main__":
    main()