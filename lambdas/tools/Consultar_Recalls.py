"""
Herramienta para consultar recalls farmacéuticos integrada con el pipeline de datos.
"""
import pandas as pd
import os
from datetime import datetime, timedelta
import json
import glob


def Consultar_Recalls(input_data, intention=None, processor=None, conn=None, session_id=None):
    """
    Consulta recalls farmacéuticos de FDA y DIGEMID según parámetros del usuario.
    
    Parámetros esperados en input_data:
    - product_name: nombre del producto a buscar
    - country: país (US, PE, o both)
    - days_back: días hacia atrás para buscar (default: 30)
    - classification: tipo de recall
    """
    try:
        # Extraer parámetros con defaults
        product_name = input_data.get('product_name', '').strip()
        country = input_data.get('country', 'both').upper()
        days_back = input_data.get('days_back', 30)
        classification = input_data.get('classification', '').strip()
        
        # Si no hay producto específico, extraer de la intención
        if not product_name and intention:
            product_name = extract_product_from_intention(intention)
        
        # Calcular fechas
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        results = []
        data_root = "data_output/curated"
        
        # Verificar si existen datos
        if not os.path.exists(data_root):
            return {
                "status": "no_data_directory",
                "message": "No se encontró el directorio de datos. ¿Has ejecutado el pipeline de ingesta?",
                "suggestion": "Ejecuta: 'actualizar datos' o 'sincronizar pipeline'"
            }
        
        # Buscar en datos de FDA (US)
        if country in ['US', 'BOTH']:
            fda_path = f"{data_root}/us_fda_enforcement"
            if os.path.exists(fda_path):
                fda_results = search_recalls_in_path(fda_path, product_name, classification, start_date, end_date, 'FDA')
                results.extend(fda_results)
        
        # Buscar en datos de DIGEMID (PE)  
        if country in ['PE', 'BOTH']:
            digemid_path = f"{data_root}/pe_digemid_alerts"
            if os.path.exists(digemid_path):
                digemid_results = search_recalls_in_path(digemid_path, product_name, classification, start_date, end_date, 'DIGEMID')
                results.extend(digemid_results)
        
        # Formatear respuesta
        if not results:
            search_summary = f"producto '{product_name}'" if product_name else "criterios especificados"
            return {
                "status": "no_results",
                "message": f"No se encontraron recalls para {search_summary} en los últimos {days_back} días.",
                "search_params": {
                    "product": product_name or "cualquiera",
                    "country": country,
                    "period": f"{start_date.strftime('%Y-%m-%d')} a {end_date.strftime('%Y-%m-%d')}",
                    "classification": classification or "cualquiera"
                },
                "suggestion": "Prueba ampliar el período de búsqueda o buscar un término más general."
            }
        
        # Ordenar por fecha más reciente y relevancia
        results = sorted(results, key=lambda x: (x.get('publication_date', ''), x.get('relevance_score', 0)), reverse=True)
        
        # Generar resumen con IA si está disponible
        ai_summary = None
        if processor and len(results) > 0:
            ai_summary = generate_recall_summary(results[:5], product_name, processor)
        
        return {
            "status": "success",
            "total_found": len(results),
            "showing": min(10, len(results)),
            "recalls": results[:10],  # Mostrar top 10
            "search_params": {
                "product": product_name or "cualquiera",
                "country": country,
                "period": f"{start_date.strftime('%Y-%m-%d')} a {end_date.strftime('%Y-%m-%d')}",
                "classification": classification or "cualquiera"
            },
            "ai_summary": ai_summary,
            "data_sources": list(set([r.get('agency') for r in results]))
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error al consultar recalls: {str(e)}",
            "suggestion": "Verifica que el pipeline de datos esté configurado correctamente."
        }


def search_recalls_in_path(base_path, product_name, classification, start_date, end_date, agency):
    """Busca recalls en archivos Parquet de una agencia específica."""
    results = []
    
    try:
        # Buscar todos los archivos parquet en la estructura year=/month=
        parquet_files = glob.glob(f"{base_path}/**/data.parquet", recursive=True)
        
        for parquet_file in parquet_files:
            if os.path.exists(parquet_file):
                try:
                    df = pd.read_parquet(parquet_file)
                    
                    # Filtro por fecha primero (más eficiente)
                    df['pub_date_parsed'] = pd.to_datetime(df['publication_date'], errors='coerce')
                    df = df.dropna(subset=['pub_date_parsed'])
                    
                    mask = (df['pub_date_parsed'] >= start_date) & (df['pub_date_parsed'] <= end_date)
                    df = df[mask]
                    
                    if df.empty:
                        continue
                    
                    # Filtrar por producto si se especifica
                    if product_name:
                        # Búsqueda flexible en múltiples campos
                        product_mask = (
                            df['product_name'].str.contains(product_name, case=False, na=False) |
                            df['recall_id'].str.contains(product_name, case=False, na=False) |
                            df['reason'].str.contains(product_name, case=False, na=False)
                        )
                        df = df[product_mask]
                        
                        # Calcular score de relevancia básico
                        df['relevance_score'] = 0
                        df.loc[df['product_name'].str.contains(product_name, case=False, na=False), 'relevance_score'] += 10
                        df.loc[df['recall_id'].str.contains(product_name, case=False, na=False), 'relevance_score'] += 5
                        df.loc[df['reason'].str.contains(product_name, case=False, na=False), 'relevance_score'] += 2
                    else:
                        df['relevance_score'] = 1
                    
                    # Filtrar por clasificación si se especifica
                    if classification:
                        class_mask = df['classification'].str.contains(classification, case=False, na=False)
                        df = df[class_mask]
                    
                    # Convertir a resultados
                    for _, row in df.iterrows():
                        results.append({
                            "recall_id": row.get('recall_id', ''),
                            "agency": agency,
                            "product_name": row.get('product_name', 'N/A'),
                            "manufacturer": row.get('manufacturer', 'N/A'), 
                            "classification": row.get('classification', 'N/A'),
                            "category": row.get('category', 'N/A'),
                            "reason": truncate_text(row.get('reason', 'N/A'), 150),
                            "publication_date": row['pub_date_parsed'].strftime('%Y-%m-%d'),
                            "countries_affected": row.get('distribution', []),
                            "relevance_score": row.get('relevance_score', 1),
                            "lot_numbers": row.get('lot_numbers', [])
                        })
                        
                except Exception as e:
                    print(f"Error processing {parquet_file}: {e}")
                    continue
    
    except Exception as e:
        print(f"Error searching in {base_path}: {e}")
    
    return results


def extract_product_from_intention(intention_text):
    """Extrae posibles nombres de productos de la intención del usuario."""
    # Palabras clave comunes de medicamentos/productos
    common_drugs = [
        'aspirina', 'ibuprofeno', 'paracetamol', 'acetaminofen', 'amoxicilina',
        'omeprazol', 'simvastatina', 'metformina', 'insulina', 'warfarina',
        'prednisona', 'furosemida', 'lisinopril', 'atorvastatina'
    ]
    
    intention_lower = intention_text.lower()
    for drug in common_drugs:
        if drug in intention_lower:
            return drug
    
    # Si no encuentra medicamentos conocidos, buscar palabras que podrían ser productos
    import re
    # Buscar palabras de 4+ letras que podrían ser nombres de productos
    potential_products = re.findall(r'\b[A-Za-z]{4,}\b', intention_text)
    
    # Filtrar palabras comunes que no son productos
    stop_words = {'recall', 'alerta', 'producto', 'medicamento', 'buscar', 'encontrar', 'dias'}
    potential_products = [p for p in potential_products if p.lower() not in stop_words]
    
    return potential_products[0] if potential_products else ""


def truncate_text(text, max_length):
    """Trunca texto a longitud máxima."""
    if not text or len(str(text)) <= max_length:
        return str(text)
    return str(text)[:max_length-3] + "..."


def generate_recall_summary(recalls, product_name, processor):
    """Genera resumen de recalls usando IA."""
    try:
        context = f"Genera un resumen conciso de estos recalls"
        if product_name:
            context += f" relacionados con '{product_name}'"
        context += ":\n\n"
        
        for i, recall in enumerate(recalls[:3], 1):
            context += f"{i}. {recall['agency']}: {recall['product_name']}\n"
            context += f"   Clasificación: {recall['classification']}\n" 
            context += f"   Razón: {recall['reason'][:100]}...\n"
            context += f"   Fecha: {recall['publication_date']}\n\n"
        
        context += "Proporciona un resumen ejecutivo en 2-3 líneas destacando los puntos más importantes para la seguridad del paciente."
        
        return processor.process_request(context)
    except Exception as e:
        return f"Error generando resumen: {str(e)}"