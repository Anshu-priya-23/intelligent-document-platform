"""Preserve visible comparative rows using geometry, independently of LLM selection.

No financial equations or dataset-specific labels/values participate in this step.
Ambiguous layouts retain the model tables and are reported for review.
"""
import re
from backend.app.schemas.extraction import Table, Value
from backend.app.services.financial_validation_service import number


def year_columns(row):
    found = []
    for word in row['words']:
        years = re.findall(r'\b(?:19|20)\d{2}\b', word['text'])
        if len(years) == 1:
            found.append((years[0], word['left'] + word['width']))
    return sorted(found, key=lambda x: x[1]) if len(found) >= 2 and len({y for y, _ in found}) == len(found) else []


def period_cells(row, columns):
    gap = min(b[1] - a[1] for a, b in zip(columns, columns[1:]))
    cells = {}
    for year, right in columns:
        words = [w for w in row['words'] if abs(w['left'] + w['width'] - right) < gap * .35]
        if len(words) == 1 and (number(words[0]['text']) is not None or words[0]['text'] in {'-', '\u2014', '\u2013'}):
            cells[year] = words[0]
    return cells


def preserve_statement_tables(data, pages):
    tables = []
    for page in pages:
        columns, schedule_x, rows, section, section_schedule, section_evidence = [], None, [], None, None, None
        for row in page.get('layout_rows', []):
            for word in row['words']:
                if not columns and word['text'].lower().strip(':') == 'schedule':
                    schedule_x = word['left'] + word['width'] / 2
            heading = year_columns(row)
            if heading:
                if rows:
                    tables.append(Table(title=f"Statement rows - page {page['page_number']}", columns=list(rows[0]), rows=rows))
                    rows = []
                columns = heading
                continue
            if not columns:
                continue
            cells = period_cells(row, columns)
            gap = min(b[1] - a[1] for a, b in zip(columns, columns[1:]))
            boundary = columns[0][1] - gap * .8
            label_words = [w for w in row['words'] if w['left'] + w['width'] < boundary]
            schedule_words = []
            if schedule_x is not None:
                schedule_words = [w for w in label_words if abs(w['left'] + w['width']/2 - schedule_x) < gap * .32]
                label_words = [w for w in label_words if w not in schedule_words]
            label = ' '.join(w['text'] for w in label_words).strip()
            if not cells:
                # Retain meaningful section headings, including their schedule note.
                heading_label = re.sub(r'^[IVXil|]+\s+', '', label)
                if label and (heading_label.isupper() or label.endswith(':') or re.match(r'^[IVX]+ EARNINGS ', label)):
                    section = label
                    section_schedule = ' '.join(w['text'] for w in schedule_words) or None
                    section_evidence = row['text']
                continue
            if len(cells) == 1 and not label:
                continue  # Page numbers are not unlabeled comparative subtotals.
            evidence = row['text']
            def value(raw):
                return Value(value=raw, source_text=evidence, page_number=page['page_number'])
            inline_schedule = re.search(r'(?i)\bschedule\s+(\d+[A-Za-z]?(?:\s*\(\d+\))?)', label)
            record = {'label': value(label or None), 'section': Value(value=section, source_text=section_evidence, page_number=page['page_number']) if section else value(None),
                      'schedule': value(' '.join(w['text'] for w in schedule_words) or (inline_schedule.group(1) if inline_schedule else None)),
                      'section_schedule': Value(value=section_schedule, source_text=section_evidence, page_number=page['page_number'])}
            for year, _ in columns:
                raw = cells.get(year, {}).get('text')
                record[year] = value(raw if raw and number(raw) is not None else None)
            rows.append(record)
        if rows:
            tables.append(Table(title=f"Statement rows - page {page['page_number']}", columns=list(rows[0]), rows=rows))
    if tables:
        # Keep model-specific extra tables; source rows are authoritative for the
        # comparative financial table, avoiding silently missing or duplicate rows.
        years = {c for t in tables for c in t.columns if re.fullmatch(r'(?:19|20)\d{2}', c)}
        data.tables = [t for t in data.tables if not any(any(y in c for y in years) for c in t.columns)] + tables
    else:
        data.issues.append('No unambiguous spatial comparative table found; review model table completeness.')
    return data


def align_statement_periods(data, kind):
    """Map unambiguous labeled source rows to canonical validation operands.

    Section context distinguishes identically named totals. Never derive a
    missing operand or choose a row because its numbers satisfy an equation.
    """
    labels = {
        'interest_earned': r'interest earned', 'other_income': r'other income',
        'interest_expended': r'interest expended', 'operating_expenses': r'operating expenses',
        'provisions_and_contingencies': r'provisions and contingencies',
        'profit_before_minority_interest': r'(?:consolidated )?net profit.*before minority interest',
        'minority_interest': r'(?:less\s*:\s*)?minority interest',
        'net_profit_attributable_to_group': r'(?:consolidated )?net profit.*attributable to (?:the )?group',
        'current_profit': r'(?:consolidated )?net profit.*attributable to (?:the )?group',
        'brought_forward_profit': r'brought forward.*profit.*',
    } if kind == 'profit_and_loss' else {}
    period_map = {}
    for period in data.periods:
        years = re.findall(r'\b(?:19|20)\d{2}\b', period.label)
        if len(years) != 1 or years[0] in period_map:
            return
        period_map[years[0]] = period
    candidates = {}
    for table in data.tables:
        if 'section_schedule' not in table.columns:
            continue
        for row in table.rows:
            label = str(row['label'].value or '').lower()
            section = re.sub(r'^[IVXil|]+\s+', '', str(row['section'].value or '')).lower()
            keys = [key for key, pattern in labels.items() if re.fullmatch(pattern, label)]
            if label in {'total', 'total assets', 'total capital and liabilities', 'total capital & liabilities'}:
                if kind == 'balance_sheet':
                    if section == 'assets': keys.append('total_assets')
                    elif section in {'capital and liabilities', 'capital & liabilities'}: keys.append('total_capital_and_liabilities')
                elif kind == 'profit_and_loss':
                    key = {'income':'total_income', 'expenditure':'total_expenditure', 'profit':'total_available_for_appropriation'}.get(section)
                    if key: keys.append(key)
            for year, period in period_map.items():
                if year not in row:
                    continue
                exact_keys = [key for key in period.fields if re.findall(r'[a-z0-9]+', key.replace('_',' ')) == re.findall(r'[a-z0-9]+', label)]
                for key in set(keys + exact_keys):
                    candidates.setdefault((year,key), []).append(row[year])
    for (year,key), values in candidates.items():
        if len(values) == 1:
            period_map[year].fields[key] = values[0].model_copy(deep=True)
