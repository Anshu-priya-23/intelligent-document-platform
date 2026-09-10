import json
from pathlib import Path

import pytest

from backend.app.schemas.extraction import Extraction
from backend.app.services.extraction_service import ground
from backend.app.services.statement_table_service import preserve_statement_tables


def empty():
    return Extraction(fields={}, tables=[], periods=[], line_items=[], tax_included=None, issues=[])


def row(*cells):
    words = [{'text':text, 'left':right-40, 'width':40, 'top':0, 'height':10} for text,right in cells]
    return {'text':' '.join(w['text'] for w in words), 'words':words}


@pytest.mark.parametrize('years', [('2028','2027'), ('2027','2028')])
def test_source_order_signs_dashes_unlabeled_totals_and_noncanonical_rows(years):
    rows = [row((years[0],500),(years[1],700)), row(('OPERATIONS',200)),
            row(('Unusual acquisition payment',250),('(31.27)',500),('12.00',700)),
            row(('Optional component',250),('-',500),('0.00',700)),
            row(('(31.27)',500),('12.00',700)), row(('479',700))]
    page = {'page_number':2, 'layout_rows':rows, 'text':'\n'.join(r['text'] for r in rows)}
    data = ground(empty(), [page], 'cash_flow_statement')
    table = data.tables[0]
    assert len(table.rows) == 3  # No footer; unnamed subtotal is retained.
    assert table.rows[0]['label'].value == 'Unusual acquisition payment'
    assert table.rows[0][years[0]].value == '(31.27)'
    assert table.rows[1][years[0]].value is None
    assert table.rows[1][years[1]].value == '0.00'
    assert table.rows[2]['label'].value is None
    assert table.rows[0][years[0]].page_number == 2


def test_inline_schedule_word_does_not_create_a_schedule_column():
    rows = [row(('2030',500),('2029',700)),
            row(('Provision (Refer schedule 18 (9))',280),('10.00',500),('5.00',700)),
            row(('Profit before income tax',280),('20.00',500),('8.00',700))]
    data = preserve_statement_tables(empty(), [{'page_number':1,'layout_rows':rows}])
    assert data.tables[0].rows[0]['label'].value == 'Provision (Refer schedule 18 (9))'
    assert data.tables[0].rows[0]['schedule'].value == '18 (9)'
    assert data.tables[0].rows[1]['label'].value == 'Profit before income tax'
    assert data.tables[0].rows[1]['schedule'].value is None


def test_no_geometry_does_not_invent_table():
    data = preserve_statement_tables(empty(), [{'page_number':1,'text':'unreadable'}])
    assert not data.tables and data.issues


@pytest.mark.parametrize('kind,count', [('balance_sheet',18),('profit_and_loss',24),('cash_flow_statement',39)])
def test_verified_source_rows_survive_empty_model_tables(kind, count):
    fixture = json.loads((Path(__file__).parent/'fixtures/statement_source_rows.json').read_text(encoding='utf-8'))[kind]
    data = ground(empty(), fixture['pages'], kind)
    actual = [r for t in data.tables for r in t.rows]
    assert len(actual) == count
    assert [[r['2026'].value,r['2025'].value] for r in actual] == fixture['expected_values']
    assert [r['schedule'].value for r in actual] == fixture['expected_schedules']
    assert not any('Unsupported evidence' in issue for issue in data.issues)


def test_source_pnl_operands_restored_for_both_periods_without_fitting_totals():
    from backend.app.schemas.extraction import Period
    from backend.app.services.financial_validation_service import validate_finances
    fixture = json.loads((Path(__file__).parent/'fixtures/statement_source_rows.json').read_text(encoding='utf-8'))['profit_and_loss']
    data = empty()
    data.periods = [Period(label=year,fields={},asset_components=[],liability_components=[],asset_components_complete=False,liability_components_complete=False) for year in ['2026','2025']]
    grounded = ground(data, fixture['pages'], 'profit_and_loss')
    assert [c['status'] for c in validate_finances('profit_and_loss', grounded)['checks']] == ['PASS'] * 10
    # Deliberately change one source total, including its evidence. It must fail,
    # not be overwritten by a calculated total or leak into the other period.
    page = fixture['pages'][0]
    for r in page['layout_rows']:
        if '495,462.81' in r['text']:
            r['text'] = r['text'].replace('495,462.81','495,999.00')
            for w in r['words']:
                w['text'] = w['text'].replace('495,462.81','495,999.00')
    page['text'] = page['text'].replace('495,462.81','495,999.00')
    changed = ground(data, [page], 'profit_and_loss')
    checks = validate_finances('profit_and_loss', changed)['checks']
    assert next(c for c in checks if c['period']=='2026' and c['name']=='total_income')['status'] == 'FAIL'
    assert all(c['status']=='PASS' for c in checks if c['period']=='2025')


def test_pdf_ocr_retains_300_dpi_small_digits(monkeypatch):
    import pymupdf
    from backend.app.services import ocr_service
    sizes = []
    def recognize(image):
        sizes.append(image.size)
        return [], 'Purchase of equipment (3,889.97) (4,075.89)'
    monkeypatch.setattr(ocr_service, 'ocr_image', recognize)
    with pymupdf.open() as doc:
        page = doc.new_page(width=612,height=792)
        page.insert_text((50,100),'(3,889.97)',fontsize=8)
        pages, used = ocr_service.extract_text(doc.tobytes(), 'application/pdf')
    assert sizes == [(2550,3300)]
    assert used and '(3,889.97)' in pages[0]['text']


def test_native_pdf_tables_have_row_evidence(monkeypatch):
    import pymupdf
    from backend.app.services.ocr_service import extract_text
    with pymupdf.open() as doc:
        page = doc.new_page()
        page.insert_text((40,40),'Comparative financial statement with native text')
        for x,text in [(350,'2028'),(450,'2027')]: page.insert_text((x,80),text)
        for x,text in [(40,'Other income'),(350,'12.00'),(450,'10.00')]: page.insert_text((x,110),text)
        pages, used = extract_text(doc.tobytes(),'application/pdf')
    assert not used
    data = ground(empty(),pages,'profit_and_loss')
    assert data.tables[0].rows[0]['2028'].value == '12.00'
