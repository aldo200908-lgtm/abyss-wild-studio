#!/usr/bin/env python3
"""Conservative soft cost ceiling, using published Release ledgers.
Public Actions are free; private jobs conservatively count every runner minute.
This DOES NOT replace GitHub/Google billing alerts or global accounting.
"""
import datetime as dt
import json
import os
from pathlib import Path
import re
import sys
import time
import requests

ROOT = Path(__file__).resolve().parent
CAP = float(os.getenv('MONTHLY_LIMIT_PEN', '20'))
USD_PEN = float(os.getenv('USD_PEN', '3.50'))
RATE = float(os.getenv('RUNNER_PRICE_USD_PER_MIN', '.006'))
IS_PRIVATE = os.getenv('REPO_PRIVATE', 'false').lower() == 'true'


def monthly_spend():
    repo = os.environ['GITHUB_REPOSITORY']
    api = f'https://api.github.com/repos/{repo}/releases'
    headers = {'Authorization': 'Bearer ' + os.environ['GH_TOKEN'],
               'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2026-03-10'}
    current = dt.datetime.now(dt.timezone.utc).strftime('%Y-%m')
    total = 0.0
    for page in range(1, 11):
        response = requests.get(api, params={'per_page': 100, 'page': page}, headers=headers, timeout=30)
        response.raise_for_status()
        releases = response.json()
        for r in releases:
            if not str(r.get('tag_name', '')).startswith('short-'):
                continue
            if not str(r.get('published_at', '')).startswith(current):
                continue
            matches = re.findall(r'^ABYSS_COST_PEN=([0-9.]+)$', r.get('body') or '', re.M)
            if matches:
                total += float(matches[-1])
        if len(releases) < 100:
            break
    return total


def check():
    spent = monthly_spend()
    # Assume up to 90 minutes for a new private-repo run, preserving the cap.
    worst = RATE * USD_PEN * 90 if IS_PRIVATE else 0.0
    print(f'Month-to-date estimate: S/{spent:.2f}, cap S/{CAP:.2f}, reserved S/{worst:.2f}', flush=True)
    if spent + worst > CAP:
        raise SystemExit('Presupuesto mensual estimado excedido. Se cancela antes de consumir la API.')


def finalize():
    report = json.loads((ROOT / 'dist' / 'reporte.json').read_text(encoding='utf-8'))
    spent = monthly_spend()
    current = float(report['runner_cost_pen_conservative'])
    # Actual run exceeds reservation? Fail closed rather than publishing.
    if spent + current > CAP:
        raise SystemExit('El consumo estimado alcanzó el tope. No publicar el archivo.')
    notes = ('Paquete generado automáticamente para descarga manual. No se publicó en YouTube.\n\n'
             f'ABYSS_COST_PEN={current:.3f}\n'
             f'ABYSS_ACTION_MINUTES={report["action_minutes_approx"]}\n'
             f'ABYSS_GEMINI_INPUT_TOKENS={report["input_tokens"]}\n'
             f'ABYSS_GEMINI_OUTPUT_TOKENS={report["output_tokens"]}\n'
             f'ABYSS_RENDER_SECONDS={report["render_seconds"]}\n'
             'La cifra es un estimado conservador de runner, no factura real.\n')
    (ROOT / 'work' / 'release-notes.txt').write_text(notes, encoding='utf-8')
    print(f'Permiso para entrega. Costo estimado acumulado S/{spent + current:.2f}', flush=True)


if __name__ == '__main__':
    if len(sys.argv) != 2 or sys.argv[1] not in ('check', 'finalize'):
        raise SystemExit('Uso: python budget.py check|finalize')
    {'check': check, 'finalize': finalize}[sys.argv[1]]()
