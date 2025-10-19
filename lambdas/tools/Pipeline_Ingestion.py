"""
Herramienta para ejecutar el pipeline de ingesta de datos farmacéuticos.
"""
import subprocess
import os
import json
from datetime import datetime, timedelta
import sys


def Pipeline_Ingestion(input_data, intention=None, processor=None, conn=None, session_id=None):
    """
    Ejecuta el pipeline de ingesta de recalls farmacéuticos.
    
    Parámetros:
    - source: 'fda', 'digemid', 'both' (default: 'both')
    - mode: 'incremental', 'backfill' (default: 'incremental')
    - days_back: para modo backfill, cuántos días hacia atrás (default: 7)
    """
    try:
        # Extraer parámetros con defaults inteligentes
        source = input_data.get('source', 'both').lower()
        mode = input_data.get('mode', 'incremental').lower()
        days_back = input_data.get('days_back', 7)
        
        # Interpretar intención si no hay parámetros explícitos
        if intention and not input_data.get('source'):
            source = interpret_source_from_intention(intention)
            
        results = []
        
        # Configurar fechas
        end_date = datetime.now().strftime('%Y-%m-%d')
        since_date = None
        
        if mode == 'backfill':
            since_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        
        print(f"🚀 Iniciando pipeline de ingesta...")
        print(f"   Fuente: {source}")
        print(f"   Modo: {mode}")
        if since_date:
            print(f"   Período: {since_date} a {end_date}")
        
        # Ejecutar para FDA si se solicita
        if source in ['fda', 'both']:
            print("📊 Ejecutando ingesta FDA...")
            fda_result = run_pipeline('us_fda_enforcement', since_date, end_date)
            results.append({
                "source": "FDA",
                "plugin_id": "us_fda_enforcement", 
                "status": fda_result["status"],
                "message": fda_result["message"],
                "records": fda_result.get("records", 0),
                "execution_time": fda_result.get("execution_time", "N/A")
            })
            print(f"   ✅ FDA: {fda_result['status']} - {fda_result.get('records', 0)} registros")
        
        # Ejecutar para DIGEMID si se solicita  
        if source in ['digemid', 'both']:
            print("🇵🇪 Ejecutando ingesta DIGEMID...")
            digemid_result = run_pipeline('pe_digemid_alerts', since_date, end_date)
            results.append({
                "source": "DIGEMID",
                "plugin_id": "pe_digemid_alerts",
                "status": digemid_result["status"],
                "message": digemid_result["message"], 
                "records": digemid_result.get("records", 0),
                "execution_time": digemid_result.get("execution_time", "N/A")
            })
            print(f"   ✅ DIGEMID: {digemid_result['status']} - {digemid_result.get('records', 0)} registros")
        
        # Resumen general
        total_records = sum(r.get("records", 0) for r in results)
        success_count = len([r for r in results if r["status"] == "success"])
        failed_sources = [r["source"] for r in results if r["status"] != "success"]
        
        # Generar mensaje de estado
        if success_count == len(results):
            status_msg = f"✅ Pipeline ejecutado exitosamente. {total_records} registros procesados."
        elif success_count > 0:
            status_msg = f"⚠️ Pipeline parcialmente exitoso. {success_count}/{len(results)} fuentes OK. Fallos: {', '.join(failed_sources)}"
        else:
            status_msg = "❌ Pipeline falló completamente. Revisar logs de error."
            
        # Verificar directorios de salida
        output_info = check_output_directories()
        
        return {
            "status": "completed" if success_count > 0 else "failed",
            "message": status_msg,
            "mode": mode,
            "total_sources": len(results),
            "successful_sources": success_count,
            "failed_sources": failed_sources,
            "total_records_ingested": total_records,
            "execution_date": end_date,
            "period": f"{since_date or 'incremental'} hasta {end_date}",
            "results": results,
            "output_directories": output_info,
            "next_steps": generate_next_steps(results, total_records)
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error ejecutando pipeline: {str(e)}",
            "suggestion": "Verifica que el pipeline esté correctamente configurado y que tengas las dependencias instaladas."
        }


def run_pipeline(plugin_id, since_date=None, until_date=None):
    """Ejecuta el orchestrator para un plugin específico."""
    start_time = datetime.now()
    
    try:
        # Verificar que el script del orchestrator existe
        orchestrator_path = "src/dataset/orchestrator.py"
        if not os.path.exists(orchestrator_path):
            return {
                "status": "error",
                "message": f"Orchestrator no encontrado en {orchestrator_path}",
                "records": 0
            }
        
        # Construir comando del orchestrator
        cmd = [
            sys.executable, '-m', 'src.dataset.orchestrator',
            '--plugin', plugin_id,
            '--output', 'data_output',
            '--log-level', 'INFO'
        ]
        
        if since_date:
            cmd.extend(['--since', since_date])
        if until_date:
            cmd.extend(['--until', until_date])
        
        print(f"   Ejecutando: {' '.join(cmd)}")
        
        # Ejecutar subprocess
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=600,  # 10 minutos timeout
            cwd=os.getcwd()
        )
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        if result.returncode == 0:
            # Parsear logs para obtener información relevante
            records = extract_records_count(result.stdout)
            watermark_info = extract_watermark_info(result.stdout)
            
            return {
                "status": "success",
                "message": f"Pipeline {plugin_id} ejecutado exitosamente",
                "records": records,
                "execution_time": f"{execution_time:.1f}s",
                "watermark": watermark_info,
                "stdout": result.stdout[-800:] if result.stdout else ""  # Últimas 800 chars
            }
        else:
            return {
                "status": "error", 
                "message": f"Pipeline {plugin_id} falló (código {result.returncode})",
                "records": 0,
                "execution_time": f"{execution_time:.1f}s",
                "error_output": result.stderr[-800:] if result.stderr else "",
                "stdout": result.stdout[-400:] if result.stdout else ""
            }
            
    except subprocess.TimeoutExpired:
        execution_time = (datetime.now() - start_time).total_seconds()
        return {
            "status": "timeout",
            "message": f"Pipeline {plugin_id} excedió tiempo límite (10min)",
            "records": 0,
            "execution_time": f"{execution_time:.1f}s"
        }
    except FileNotFoundError:
        return {
            "status": "error",
            "message": f"Python o módulo {plugin_id} no encontrado. Verifica la instalación.",
            "records": 0,
            "execution_time": "0s"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Error ejecutando {plugin_id}: {str(e)}",
            "records": 0,
            "execution_time": "0s"
        }


def extract_records_count(log_output):
    """Extrae el número de registros procesados de los logs."""
    try:
        import re
        
        if not log_output:
            return 0
        
        # Pattern: "Wrote curated rows=X to ..."
        match = re.search(r'Wrote curated rows=(\d+)', log_output)
        if match:
            return int(match.group(1))
            
        # Pattern: "Fetched raw records=X"  
        match = re.search(r'Fetched raw records=(\d+)', log_output)
        if match:
            return int(match.group(1))
        
        # Pattern: "normalized records=X"
        match = re.search(r'normalized.*?(\d+)', log_output, re.IGNORECASE)
        if match:
            return int(match.group(1))
            
        return 0
        
    except Exception:
        return 0


def extract_watermark_info(log_output):
    """Extrae información del watermark de los logs."""
    try:
        import re
        
        if not log_output:
            return None
        
        # Buscar mensajes sobre watermarks
        watermark_match = re.search(r'watermark.*?(\d{4}-\d{2}-\d{2})', log_output, re.IGNORECASE)
        if watermark_match:
            return watermark_match.group(1)
        
        return None
    except Exception:
        return None


def interpret_source_from_intention(intention_text):
    """Interpreta qué fuente de datos quiere el usuario basado en su intención."""
    intention_lower = intention_text.lower()
    
    if 'fda' in intention_lower:
        return 'fda'
    elif 'digemid' in intention_lower or 'peru' in intention_lower:
        return 'digemid'
    elif 'ambos' in intention_lower or 'todo' in intention_lower:
        return 'both'
    else:
        return 'both'  # Default a ambos


def check_output_directories():
    """Verifica el estado de los directorios de salida."""
    info = {
        "raw_exists": os.path.exists("data_output/raw"),
        "curated_exists": os.path.exists("data_output/curated"),
        "state_exists": os.path.exists("data_output/.state")
    }
    
    # Contar archivos en cada directorio
    if info["raw_exists"]:
        try:
            import glob
            raw_files = glob.glob("data_output/raw/**/data.jsonl", recursive=True)
            info["raw_files_count"] = len(raw_files)
        except:
            info["raw_files_count"] = 0
    
    if info["curated_exists"]:
        try:
            import glob
            curated_files = glob.glob("data_output/curated/**/data.parquet", recursive=True)
            info["curated_files_count"] = len(curated_files)
        except:
            info["curated_files_count"] = 0
    
    return info


def generate_next_steps(results, total_records):
    """Genera sugerencias de próximos pasos basados en los resultados."""
    if total_records == 0:
        return [
            "Verifica la conectividad a internet",
            "Revisa los logs de error para más detalles", 
            "Prueba ejecutar el pipeline manualmente desde terminal"
        ]
    
    steps = [
        f"Consulta los {total_records} registros usando 'buscar recalls'",
        "Genera un resumen con 'resumen de alertas'",
    ]
    
    failed_count = len([r for r in results if r["status"] != "success"])
    if failed_count > 0:
        steps.append("Revisa los errores de las fuentes que fallaron")
    
    return steps