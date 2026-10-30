"""Entrena el Random Forest que sugiere el tipo de campaña y guarda sus métricas.

Uso (desde backend/):  python -m ml.entrenar
Genera: ml/dataset_sintetico.csv, ml/encuestas_validacion_etiquetadas.csv, ml/modelo.joblib, ml/metricas.json
"""
import json
from datetime import datetime

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from app.config import HORA_PERU, cargar_tipos_campana
from app.services.ml import CATEGORICAS, NUMERICAS, RUTA_METRICAS, RUTA_MODELO, VARIABLES
from ml import generar_dataset

SEMILLA = 42


def crear_modelo(arboles: int = 100) -> Pipeline:
    """Texto → columnas 0/1 (one-hot) y luego el bosque aleatorio."""
    preparar = ColumnTransformer(
        [("cat", OneHotEncoder(handle_unknown="ignore"), CATEGORICAS)], remainder="passthrough"
    )
    bosque = RandomForestClassifier(
        n_estimators=arboles, min_samples_leaf=2, class_weight="balanced", random_state=SEMILLA
    )
    return Pipeline([("preparar", preparar), ("bosque", bosque)])


def importancia_por_variable(modelo: Pipeline) -> list[dict]:
    """Suma la importancia de las columnas one-hot para volver a la variable original."""
    nombres = modelo.named_steps["preparar"].get_feature_names_out()
    importancias = modelo.named_steps["bosque"].feature_importances_
    total = dict.fromkeys(VARIABLES, 0.0)
    for nombre, valor in zip(nombres, importancias):
        columna = nombre.split("__", 1)[1]
        variable = columna if columna in NUMERICAS else next(c for c in CATEGORICAS if columna.startswith(c + "_"))
        total[variable] += float(valor)
    return [{"variable": v, "valor": round(i, 4)} for v, i in sorted(total.items(), key=lambda x: -x[1])]


def evaluar(sintetico: pd.DataFrame, reales: pd.DataFrame, arboles: int = 100) -> tuple[Pipeline, dict]:
    """Valida con datos sintéticos (80/20 y validación cruzada) y con las encuestas de validación.

    Devuelve el modelo final, entrenado con TODO el dataset sintético, y las métricas.
    """
    x, y = sintetico[VARIABLES], sintetico["tipo"]
    x_ent, x_pru, y_ent, y_pru = train_test_split(x, y, test_size=0.2, stratify=y, random_state=SEMILLA)

    pliegues = StratifiedKFold(n_splits=5, shuffle=True, random_state=SEMILLA)
    cv = cross_val_score(crear_modelo(arboles), x_ent, y_ent, cv=pliegues, scoring="f1_macro")

    modelo = crear_modelo(arboles).fit(x_ent, y_ent)
    pred = modelo.predict(x_pru)
    etiquetas = sorted(y.unique())
    reporte = classification_report(y_pru, pred, labels=etiquetas, output_dict=True, zero_division=0)

    # Modelo final con todos los datos sintéticos; se evalúa con las encuestas de validación (nunca vistas)
    final = crear_modelo(arboles).fit(x, y)
    pred_reales = final.predict(reales[VARIABLES])
    conf_reales = final.predict_proba(reales[VARIABLES]).max(axis=1)

    metricas = {
        "fecha": datetime.now(HORA_PERU).strftime("%d/%m/%Y %H:%M"),
        "arboles": arboles,
        "variables": VARIABLES,
        "n_sintetico": len(sintetico),
        "n_entrenamiento": len(x_ent),
        "n_prueba": len(x_pru),
        "validacion_cruzada": {"f1_macro_media": round(cv.mean(), 3), "f1_macro_desv": round(cv.std(), 3)},
        "prueba": {
            "exactitud": round(accuracy_score(y_pru, pred), 3),
            "f1_macro": round(f1_score(y_pru, pred, average="macro"), 3),
            "por_tipo": {
                t: {"precision": round(reporte[t]["precision"], 2), "recall": round(reporte[t]["recall"], 2),
                    "f1": round(reporte[t]["f1-score"], 2), "soporte": int(reporte[t]["support"])}
                for t in etiquetas
            },
            "matriz": {"etiquetas": etiquetas, "valores": confusion_matrix(y_pru, pred, labels=etiquetas).tolist()},
        },
        "reales": {
            "n": len(reales),
            "exactitud": round(accuracy_score(reales["tipo"], pred_reales), 3),
            "tipos_sin_ejemplos": [t for t in etiquetas if t not in set(reales["tipo"])],
            "filas": [
                {"necesidad": r["necesidad"], "sector": r["sector"], "real": r["tipo"], "predicho": str(p),
                 "acierto": r["tipo"] == p, "confianza": round(float(c) * 100, 1)}
                for (_, r), p, c in zip(reales.iterrows(), pred_reales, conf_reales)
            ],
        },
        "importancia": importancia_por_variable(final),
    }
    return final, metricas


def main():
    tipos = cargar_tipos_campana()
    sintetico, reales = generar_dataset.generar(), generar_dataset.reales()
    faltan = set(sintetico["tipo"]) ^ set(tipos)
    if faltan:
        raise SystemExit(f"Los tipos del dataset y de config/tipos_campana.yaml no coinciden: {faltan}")
    sintetico.to_csv(RUTA_MODELO.parent / "dataset_sintetico.csv", index=False, encoding="utf-8")
    reales.to_csv(RUTA_MODELO.parent / "encuestas_validacion_etiquetadas.csv", index=False, encoding="utf-8")

    modelo, metricas = evaluar(sintetico, reales)
    joblib.dump(modelo, RUTA_MODELO, compress=3)
    RUTA_METRICAS.write_text(json.dumps(metricas, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Dataset sintético: {metricas['n_sintetico']} clientes, {len(tipos)} tipos de campaña")
    print(f"Validación cruzada (F1 macro): {metricas['validacion_cruzada']['f1_macro_media']} "
          f"± {metricas['validacion_cruzada']['f1_macro_desv']}")
    print(f"Prueba sintética: exactitud {metricas['prueba']['exactitud']} · F1 macro {metricas['prueba']['f1_macro']}")
    print(f"Encuestas de validación (nunca vistas): exactitud {metricas['reales']['exactitud']} "
          f"({sum(f['acierto'] for f in metricas['reales']['filas'])}/{metricas['reales']['n']})")
    for f in metricas["reales"]["filas"]:
        if not f["acierto"]:
            print(f"   fallo: {f['necesidad'][:55]:<55} real={f['real']} predicho={f['predicho']}")
    print("Importancia:", ", ".join(f"{i['variable']} {i['valor']:.2f}" for i in metricas["importancia"][:5]))
    print(f"Modelo guardado en {RUTA_MODELO} ({RUTA_MODELO.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
