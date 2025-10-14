from pymongo import MongoClient
from collections import defaultdict, Counter
from tqdm import tqdm

client = MongoClient("mongodb://localhost:27017/")
db = client["off"]
col = db["products_with_ingredients_no_petfood"]

# 🧩 Filtro: sólo productos con ingredients_text no vacío ni nulo
filtro = {"ingredients_text": {"$exists": True, "$nin": ["", None]}}

# 📊 Conteo exacto
exact_total = col.count_documents(filtro)
print("Exacto (con ingredients_text válido):", exact_total, "documentos")

# Obtener columnas
projection = list(col.find_one().keys())

stats = defaultdict(Counter)
coverage = Counter()
total = 0

cursor = col.find(filtro, projection, no_cursor_timeout=True).batch_size(1000)
try:
    for doc in tqdm(cursor, desc="Profiling OFF (ingredients_text ≠ '')"):
        total += 1
        for k, v in doc.items():
            if v in (None, "", "null"):
                continue
            coverage[k] += 1
            if isinstance(v, (list, dict)):
                v = str(v)
            stats[k][v] += 1
finally:
    cursor.close()

# 📝 Exportar
with open("mongo_column_stats_ingredients.txt", "w", encoding="utf-8") as f:
    for colname in sorted(projection):
        cov = 100.0 * coverage[colname] / max(total, 1)
        f.write(f"Column: {colname} | Coverage: {cov:.1f}% | Unique: {len(stats[colname])}\n")
        f.write(f"  Most common: {stats[colname].most_common(3)}\n\n")

print(f"✅ Stats saved to mongo_column_stats_ingredients.txt ({total} docs analizados)")
