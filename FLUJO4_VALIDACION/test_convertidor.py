"""
Pruebas del Convertidor Texto → Números
========================================
Ejecutar: python test_convertidor.py
"""

from convertidor_texto_numeros import ConvertidorTextoNumeros


def main():
    conv = ConvertidorTextoNumeros()
    print(conv.info())
    errores = 0

    # ── Pruebas de conversión exacta ──
    print("\n" + "═" * 60)
    print(" PRUEBAS DE CONVERSIÓN EXACTA")
    print("═" * 60)

    pruebas_exactas = [
        ("cero", 0), ("Uno", 1), ("Quince", 15), ("Veinticinco", 25),
        ("Treinta y cinco", 35), ("cuarenta y dos", 42), ("Cien", 100),
        ("Ciento diez", 110), ("Doscientos", 200),
        ("Trescientos cuarenta y cinco", 345), ("Cuatrocientos veintiuno", 421),
        ("Quinientos cuarenta y cinco", 545), ("Seiscientos treinta y Cinco", 635),
        ("Novecientos noventa y nueve", 999), ("Ochocientos", 800),
    ]

    for texto, esperado in pruebas_exactas:
        resultado = conv.convertir(texto)
        ok = resultado == esperado
        if not ok:
            errores += 1
        print(f"  {'✅' if ok else '❌'} '{texto}' → {resultado} (esperado: {esperado})")

    # ── Pruebas de conversión difusa ──
    print("\n" + "═" * 60)
    print(" PRUEBAS DE CONVERSIÓN DIFUSA (OCR corrupto)")
    print("═" * 60)

    pruebas_fuzzy = [
        ("Calorce", 14), ("veinisinco", 25), ("Venticinco", 25),
        ("Selcarta", None), ("treivila", None), ("Ochodeutos", 800),
        ("Despula", None), ("Quinits", None), ("diecinneve", 19),
        ("sincuenta", 50), ("cuaranta", 40),
    ]

    for texto, esperado in pruebas_fuzzy:
        resultado, conf = conv.convertir_fuzzy(texto)
        ok = resultado == esperado
        if not ok:
            errores += 1
        print(f"  {'✅' if ok else '❌'} '{texto}' → {resultado} [{conf:.0%}] (esperado: {esperado})")

    # ── Pruebas del flujo completo ──
    print("\n" + "═" * 60)
    print(" PRUEBAS DEL FLUJO COMPLETO (validar_campo)")
    print("═" * 60)

    pruebas_campo = [
        ("Quinientos cuarenta y cinco", "545", 545, 1.0),
        ("Quinientos cuarenta y cinco", "544", 545, 1.0),
        ("Calorce", "14", 14, 0.85),
        ("Calorce", "11", 14, 0.85),
        ("Treinta y Cinco", "035", 35, 1.0),
        ("Cincuenta", "050", 50, 1.0),
        ("Ochocientos", "800", 800, 1.0),
    ]

    for texto, digito, esperado_val, esperado_conf_min in pruebas_campo:
        res = conv.validar_campo(texto, digito)
        val, conf, metodo = res['valor'], res['confianza'], res['metodo']
        ok = val == esperado_val and conf >= esperado_conf_min
        if not ok:
            errores += 1
        print(f"  {'✅' if ok else '❌'} '{texto}' / '{digito}' → {val} [{conf:.0%}] vía {metodo}")

    # ── Resumen ──
    total = len(pruebas_exactas) + len(pruebas_fuzzy) + len(pruebas_campo)
    print(f"\n{'═' * 60}")
    print(f" RESULTADO: {total - errores}/{total} pruebas pasadas {'✅' if errores == 0 else '❌'}")
    print(f"{'═' * 60}")


if __name__ == "__main__":
    main()
