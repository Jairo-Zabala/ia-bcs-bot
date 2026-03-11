#!/usr/bin/env python3
"""
Despliega el dashboard de auditoría de seguridad como Azure Monitor Workbook.

Requisitos:
  - Azure CLI autenticado (az login)
  - Resource group rg-bcs-bot existente

Uso:
  python docs/deploy_dashboard_azure.py
"""

import json
import os
import subprocess
import sys
import uuid

# Existing workbook GUID (set to update instead of creating new)
EXISTING_GUID = os.environ.get("WORKBOOK_GUID", "")

# ═══════════════════════════════════════════════════
# CONFIGURACIÓN  (ajustar si cambia la infra)
# ═══════════════════════════════════════════════════
RESOURCE_GROUP = "rg-bcs-bot"
LOCATION = "eastus2"
WORKSPACE_NAME = "law-bcs-bot"
WORKBOOK_DISPLAY_NAME = "Auditoría de Seguridad - BCS Bot"
DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "audit_data.json")


# ═══════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════
def az(args):
    """Run an Azure CLI command, return (exit_code, stdout, stderr)."""
    result = subprocess.run(
        ["az"] + args, capture_output=True, text=True
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def az_or_die(args, msg="Error en Azure CLI"):
    rc, out, err = az(args)
    if rc != 0:
        print(f"✗ {msg}: {err}")
        sys.exit(1)
    return out


def kql(value):
    """Escape a Python string as a KQL single-quoted string literal."""
    return "'" + str(value).replace("'", "''") + "'"


# ═══════════════════════════════════════════════════
# 1. LOG ANALYTICS WORKSPACE
# ═══════════════════════════════════════════════════
def ensure_workspace():
    print("\n🔍 Verificando Log Analytics workspace...")
    rc, out, _ = az([
        "monitor", "log-analytics", "workspace", "show",
        "--resource-group", RESOURCE_GROUP,
        "--workspace-name", WORKSPACE_NAME,
        "--query", "id", "-o", "tsv",
    ])
    if rc == 0 and out:
        print(f"   ✓ {WORKSPACE_NAME} ya existe")
        return out

    print(f"   Creando {WORKSPACE_NAME} (PerGB2018, 30d retención)...")
    az_or_die([
        "monitor", "log-analytics", "workspace", "create",
        "--resource-group", RESOURCE_GROUP,
        "--workspace-name", WORKSPACE_NAME,
        "--location", LOCATION,
        "--sku", "PerGB2018",
        "--retention-time", "30",
    ], "No se pudo crear workspace")

    out = az_or_die([
        "monitor", "log-analytics", "workspace", "show",
        "--resource-group", RESOURCE_GROUP,
        "--workspace-name", WORKSPACE_NAME,
        "--query", "id", "-o", "tsv",
    ])
    print(f"   ✓ Workspace creado")
    return out


# ═══════════════════════════════════════════════════
# 2. KQL DATATABLE BUILDERS
# ═══════════════════════════════════════════════════
def build_findings_kql(findings):
    """Generate a KQL datatable() expression with all findings."""
    cols = (
        "ID:string, Severidad:string, Normativa:string, Control:string, "
        "Hallazgo:string, Ubicacion:string, Riesgo:string, "
        "Remediacion:string, Estado:string, Plazo:string"
    )
    rows = []
    for f in findings:
        rows.append(", ".join([
            kql(f["ID"]),
            kql(f["Severidad"]),
            kql(f["Normativa"]),
            kql(f.get("Control / Referencia", "")),
            kql(f["Hallazgo"]),
            kql(f.get("Ubicación", "")),
            kql(f.get("Descripción del Riesgo", "")),
            kql(f.get("Remediación", "")),
            kql(f.get("Estado", "")),
            kql(f.get("Plazo", "")),
        ]))
    return f"datatable({cols})[\n" + ",\n".join(rows) + "\n]"


def build_plan_kql(plan):
    """Generate a KQL datatable() expression with the remediation plan."""
    cols = (
        "Prioridad:string, Fase:string, IDHallazgo:string, "
        "Accion:string, Responsable:string, Plazo:string, "
        "Esfuerzo:string, Estado:string"
    )
    rows = []
    for p in plan:
        rows.append(", ".join([
            kql(p["Prioridad"]),
            kql(p["Fase"]),
            kql(p["ID Hallazgo"]),
            kql(p["Acción"]),
            kql(p["Responsable"]),
            kql(p["Plazo"]),
            kql(p["Esfuerzo Estimado"]),
            kql(p["Estado"]),
        ]))
    return f"datatable({cols})[\n" + ",\n".join(rows) + "\n]"


# ═══════════════════════════════════════════════════
# 3. WORKBOOK TEMPLATE
# ═══════════════════════════════════════════════════
def build_workbook(findings_dt, plan_dt, workspace_id):
    """Build the Azure Workbook JSON content."""

    sev_order = (
        "| order by case("
        "Severidad == 'Crítico', 1, "
        "Severidad == 'Alto', 2, "
        "Severidad == 'Medio', 3, 4) asc"
    )

    sev_thresholds = [
        {"operator": "==", "thresholdValue": "Crítico", "representation": "redBright", "text": "{0}{1}"},
        {"operator": "==", "thresholdValue": "Alto", "representation": "orange", "text": "{0}{1}"},
        {"operator": "==", "thresholdValue": "Medio", "representation": "yellow", "text": "{0}{1}"},
        {"operator": "==", "thresholdValue": "Bajo", "representation": "green", "text": "{0}{1}"},
        {"operator": "Default", "representation": "blue", "text": "{0}{1}"},
    ]

    prio_thresholds = [
        {"operator": "==", "thresholdValue": "P1", "representation": "redBright", "text": "{0}{1}"},
        {"operator": "==", "thresholdValue": "P2", "representation": "orange", "text": "{0}{1}"},
        {"operator": "==", "thresholdValue": "P3", "representation": "yellow", "text": "{0}{1}"},
        {"operator": "==", "thresholdValue": "P4", "representation": "green", "text": "{0}{1}"},
        {"operator": "Default", "representation": "blue", "text": "{0}{1}"},
    ]

    items = [
        # ── Header ──
        {
            "type": 1,
            "content": {
                "json": (
                    "# 🏦 Auditoría de Seguridad — Asesor Virtual BCS\n"
                    "---\n"
                    "**Fecha:** Marzo 2026 · **Scope:** Flask + Azure OpenAI GPT-4o-mini "
                    "+ Azure Speech (TTS/STT) en AKS\n\n"
                    "**Normativas:** ISO 27001:2022 · OWASP Top 10 · OWASP API Security "
                    "· OWASP LLM Top 10 · CIS Docker/K8s · SFC 007/2018 · Ley 1581/2012"
                )
            },
            "name": "header",
        },

        # ── Hidden default parameters (so queries run on initial load) ──
        {
            "type": 9,
            "content": {
                "version": "KqlParameterItem/1.0",
                "parameters": [
                    {
                        "id": "a1b2c3d4-0001-0001-0001-000000000001",
                        "version": "KqlParameterItem/1.0",
                        "name": "SelectedSev",
                        "type": 1,
                        "value": "",
                        "isHiddenWhenLocked": True,
                    },
                    {
                        "id": "a1b2c3d4-0001-0001-0001-000000000002",
                        "version": "KqlParameterItem/1.0",
                        "name": "SelectedNorm",
                        "type": 1,
                        "value": "",
                        "isHiddenWhenLocked": True,
                    },
                ],
                "style": "pills",
                "queryType": 0,
                "resourceType": "microsoft.operationalinsights/workspaces",
            },
            "name": "hidden-params",
        },

        # ── KPI Tiles (interactive — exports SelectedSev) ──
        {
            "type": 3,
            "content": {
                "version": "KqlItem/1.0",
                "query": (
                    f"let data = {findings_dt};\n"
                    "data\n"
                    "| summarize Cantidad = count() by Severidad\n"
                    "| union (data | summarize Cantidad = count() | extend Severidad = 'TOTAL')\n"
                    f"{sev_order}"
                ),
                "size": 4,
                "queryType": 0,
                "resourceType": "microsoft.operationalinsights/workspaces",
                "visualization": "tiles",
                "tileSettings": {
                    "titleContent": {
                        "columnMatch": "Severidad",
                        "formatter": 1,
                    },
                    "leftContent": {
                        "columnMatch": "Cantidad",
                        "formatter": 12,
                        "formatOptions": {"palette": "auto"},
                        "numberFormat": {
                            "unit": 17,
                            "options": {
                                "style": "decimal",
                                "maximumFractionDigits": 0,
                            },
                        },
                    },
                    "showBorder": True,
                },
                "exportFieldName": "Severidad",
                "exportParameterName": "SelectedSev",
            },
            "name": "kpi-tiles",
        },

        # ── Severity Donut (33%) — filtered by SelectedSev ──
        {
            "type": 3,
            "content": {
                "version": "KqlItem/1.0",
                "query": (
                    f"let data = {findings_dt};\n"
                    "data\n"
                    "| where '{SelectedSev}' == '' or '{SelectedSev}' == 'TOTAL' or Severidad == '{SelectedSev}'\n"
                    "| summarize Cantidad = count() by Severidad"
                ),
                "size": 2,
                "title": "Distribución por Severidad",
                "queryType": 0,
                "resourceType": "microsoft.operationalinsights/workspaces",
                "visualization": "piechart",
                "chartSettings": {
                    "seriesLabelSettings": [
                        {"seriesName": "Crítico", "color": "redBright"},
                        {"seriesName": "Alto", "color": "orange"},
                        {"seriesName": "Medio", "color": "yellow"},
                        {"seriesName": "Bajo", "color": "green"},
                    ]
                },
            },
            "customWidth": "33",
            "name": "severity-donut",
        },

        # ── Normativa Bar (33%) — filtered by SelectedSev, exports SelectedNorm ──
        {
            "type": 3,
            "content": {
                "version": "KqlItem/1.0",
                "query": (
                    f"let data = {findings_dt};\n"
                    "data\n"
                    "| where '{SelectedSev}' == '' or '{SelectedSev}' == 'TOTAL' or Severidad == '{SelectedSev}'\n"
                    "| summarize Cantidad = count() by Normativa\n"
                    "| order by Cantidad desc"
                ),
                "size": 2,
                "title": "Hallazgos por Normativa",
                "queryType": 0,
                "resourceType": "microsoft.operationalinsights/workspaces",
                "visualization": "barchart",
                "exportFieldName": "Normativa",
                "exportParameterName": "SelectedNorm",
            },
            "customWidth": "33",
            "name": "normativa-bar",
        },

        # ── Plan Bar (34%) — filtered by SelectedSev ──
        {
            "type": 3,
            "content": {
                "version": "KqlItem/1.0",
                "query": (
                    f"let data = {plan_dt};\n"
                    "data\n"
                    "| where '{SelectedSev}' == '' or '{SelectedSev}' == 'TOTAL'\n"
                    "    or ('{SelectedSev}' == 'Crítico' and Prioridad == 'P1')\n"
                    "    or ('{SelectedSev}' == 'Alto' and Prioridad == 'P2')\n"
                    "    or ('{SelectedSev}' == 'Medio' and Prioridad == 'P3')\n"
                    "    or ('{SelectedSev}' == 'Bajo' and Prioridad == 'P4')\n"
                    "| summarize Acciones = count() by Prioridad\n"
                    "| order by Prioridad asc"
                ),
                "size": 2,
                "title": "Plan de Remediación por Prioridad",
                "queryType": 0,
                "resourceType": "microsoft.operationalinsights/workspaces",
                "visualization": "barchart",
                "chartSettings": {
                    "seriesLabelSettings": [
                        {"seriesName": "Acciones", "color": "blue"},
                    ]
                },
            },
            "customWidth": "34",
            "name": "plan-bar",
        },

        # ── Findings Section ──
        {
            "type": 1,
            "content": {"json": "## 📋 Hallazgos de Seguridad"},
            "name": "findings-title",
        },
        {
            "type": 3,
            "content": {
                "version": "KqlItem/1.0",
                "query": (
                    f"let data = {findings_dt};\n"
                    "data\n"
                    "| where ('{SelectedSev}' == '' or '{SelectedSev}' == 'TOTAL' or Severidad == '{SelectedSev}')\n"
                    "    and ('{SelectedNorm}' == '' or Normativa == '{SelectedNorm}')\n"
                    f"{sev_order}"
                ),
                "size": 0,
                "showAnalytics": True,
                "showExportToExcel": True,
                "queryType": 0,
                "resourceType": "microsoft.operationalinsights/workspaces",
                "visualization": "table",
                "gridSettings": {
                    "formatters": [
                        {
                            "columnMatch": "Severidad",
                            "formatter": 18,
                            "formatOptions": {
                                "thresholdsOptions": "colors",
                                "thresholdsGrid": sev_thresholds,
                            },
                        },
                        {
                            "columnMatch": "Riesgo",
                            "formatter": 1,
                            "formatOptions": {
                                "linkTarget": "CellDetails",
                                "linkIsContextBlade": True,
                            },
                        },
                        {
                            "columnMatch": "Remediacion",
                            "formatter": 1,
                            "formatOptions": {
                                "linkTarget": "CellDetails",
                                "linkIsContextBlade": True,
                            },
                        },
                    ],
                    "filter": True,
                    "sortBy": [{"itemKey": "Severidad", "sortOrder": 1}],
                },
            },
            "name": "findings-grid",
        },

        # ── Plan Section ──
        {
            "type": 1,
            "content": {"json": "## 🔧 Plan de Remediación"},
            "name": "plan-title",
        },
        {
            "type": 3,
            "content": {
                "version": "KqlItem/1.0",
                "query": (
                    f"let data = {plan_dt};\n"
                    "data\n"
                    "| where '{SelectedSev}' == '' or '{SelectedSev}' == 'TOTAL'\n"
                    "    or ('{SelectedSev}' == 'Crítico' and Prioridad == 'P1')\n"
                    "    or ('{SelectedSev}' == 'Alto' and Prioridad == 'P2')\n"
                    "    or ('{SelectedSev}' == 'Medio' and Prioridad == 'P3')\n"
                    "    or ('{SelectedSev}' == 'Bajo' and Prioridad == 'P4')\n"
                    "| order by Prioridad asc"
                ),
                "size": 0,
                "showAnalytics": True,
                "showExportToExcel": True,
                "queryType": 0,
                "resourceType": "microsoft.operationalinsights/workspaces",
                "visualization": "table",
                "gridSettings": {
                    "formatters": [
                        {
                            "columnMatch": "Prioridad",
                            "formatter": 18,
                            "formatOptions": {
                                "thresholdsOptions": "colors",
                                "thresholdsGrid": prio_thresholds,
                            },
                        },
                    ],
                    "filter": True,
                },
            },
            "name": "plan-grid",
        },
    ]

    return {
        "version": "Notebook/1.0",
        "items": items,
        "fallbackResourceIds": [workspace_id],
        "isLocked": False,
    }


# ═══════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════
def main():
    print("=" * 55)
    print("  Azure Monitor Workbook — Auditoría BCS Bot")
    print("=" * 55)

    # Verify data
    if not os.path.exists(DATA_PATH):
        print(f"\n✗ No se encontró {DATA_PATH}")
        print("  Ejecuta primero: python docs/exportar_json.py")
        sys.exit(1)

    with open(DATA_PATH) as f:
        data = json.load(f)
    print(f"\n📊 Datos: {len(data['findings'])} hallazgos, {len(data['plan'])} acciones de remediación")

    # Verify Azure auth
    rc, _, _ = az(["account", "show"])
    if rc != 0:
        print("\n✗ No estás autenticado. Ejecuta: az login")
        sys.exit(1)

    # 1. Ensure workspace
    workspace_id = ensure_workspace()

    # 2. Build KQL + workbook
    print("\n📝 Generando workbook template...")
    findings_dt = build_findings_kql(data["findings"])
    plan_dt = build_plan_kql(data["plan"])
    workbook = build_workbook(findings_dt, plan_dt, workspace_id)
    serialized = json.dumps(workbook, ensure_ascii=False)

    # Save template locally for reference
    tpl_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "azure-workbook-auditoria.json")
    with open(tpl_path, "w") as f:
        json.dump(workbook, f, indent=2, ensure_ascii=False)
    print(f"   ✓ Template guardado: docs/azure-workbook-auditoria.json")

    # 3. Deploy workbook via ARM REST API
    workbook_guid = EXISTING_GUID or (sys.argv[1] if len(sys.argv) > 1 else str(uuid.uuid4()))
    sub_id = az_or_die(["account", "show", "--query", "id", "-o", "tsv"])

    arm_url = (
        f"https://management.azure.com/subscriptions/{sub_id}"
        f"/resourceGroups/{RESOURCE_GROUP}"
        f"/providers/Microsoft.Insights/workbooks/{workbook_guid}"
        f"?api-version=2023-06-01"
    )

    arm_body = {
        "location": LOCATION,
        "kind": "shared",
        "properties": {
            "displayName": WORKBOOK_DISPLAY_NAME,
            "serializedData": serialized,
            "category": "workbook",
            "sourceId": workspace_id,
        },
    }

    # Write body to temp file to avoid shell escaping issues
    body_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_arm_body.json")
    with open(body_path, "w") as f:
        json.dump(arm_body, f, ensure_ascii=False)

    print(f"\n🚀 Desplegando workbook en Azure (rg-bcs-bot / {LOCATION})...")

    rc, out, err = az([
        "rest", "--method", "PUT",
        "--url", arm_url,
        "--body", f"@{body_path}",
    ])

    # Cleanup temp file
    try:
        os.unlink(body_path)
    except OSError:
        pass

    if rc != 0:
        print(f"\n✗ Error desplegando workbook:\n{err}")
        debug_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "debug-serialized.json")
        with open(debug_path, "w") as f:
            f.write(serialized)
        print(f"  (Template guardado en {debug_path} para debug)")
        sys.exit(1)

    portal_url = (
        f"https://portal.azure.com/#/resource/subscriptions/{sub_id}"
        f"/resourceGroups/{RESOURCE_GROUP}/providers/Microsoft.Insights"
        f"/workbooks/{workbook_guid}/workbook"
    )

    print(f"\n{'=' * 55}")
    print("  ✅ Dashboard desplegado en Azure exitosamente!")
    print(f"{'=' * 55}")
    print(f"\n📌 Abrir en Azure Portal:")
    print(f"   {portal_url}")
    print(f"\n📂 O navegar manualmente:")
    print(f"   Azure Portal → Monitor → Workbooks → '{WORKBOOK_DISPLAY_NAME}'")
    print()


if __name__ == "__main__":
    main()
