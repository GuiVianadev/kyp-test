import json
import logging
from datetime import datetime

logger = logging.getLogger(__name__)
if not logger.handlers:
    logger.addHandler(logging.NullHandler())


def extract_financial_data_tool(duplicata_json: str) -> dict:
    """Extract and structure financial data from duplicata JSON.
    
    This tool parses the raw duplicata JSON document and extracts key financial
    metrics needed for credit analysis. It validates data completeness, converts
    values to standardized formats, calculates derived metrics, and performs
    preliminary risk scoring.
    
    The tool performs the following steps:
    1. Parse and validate JSON structure
    2. Extract balance sheet items (assets, liabilities, equity)
    3. Extract income statement items (revenue, expenses, profit)
    4. Extract cash flow and payment history
    5. Calculate derived metrics (working capital, current ratio, red flags)
    6. Perform deterministic risk scoring based on financial health indicators
    7. Validate data completeness and flag missing fields
    
    Args:
        duplicata_json: JSON string containing complete duplicata data.
                       Must include empresa, duplicata, and financeiro sections.
                       
                       Expected structure:
                       {
                         "empresa": {
                           "cnpj": str,
                           "razao_social": str,
                           "setor": str
                         },
                         "duplicata": {
                           "valor": float,
                           "vencimento": str (ISO date)
                         },
                         "financeiro": {
                           "balanco_patrimonial": {...},
                           "dre": {...},
                           "historico_pagamentos": [...]
                         }
                       }
    
    Returns:
        Dictionary with structured financial data, risk analysis, and extraction status.
        
        Success response structure:
        {
            'status': 'success',
            'empresa': {
                'cnpj': str,
                'razao_social': str,
                'setor': str
            },
            'duplicata': {
                'valor': float,
                'vencimento': str
            },
            'balanco': {
                'ativo_circulante': float,
                'ativo_nao_circulante': float,
                'ativo_total': float,
                'passivo_circulante': float,
                'passivo_nao_circulante': float,
                'passivo_total': float,
                'patrimonio_liquido': float
            },
            'dre': {
                'receita_bruta': float,
                'receita_liquida': float,
                'lucro_bruto': float,
                'lucro_operacional': float,
                'lucro_liquido': float,
                'ebitda': float
            },
            'historico': {
                'total_operacoes': int,
                'operacoes_pagas': int,
                'atrasos': int,
                'ticket_medio': float
            },
            'derived_metrics': {
                'capital_giro': float,
                'patrimonio_liquido_tangivel': float,
                'liquidez_corrente': float,
                'calculated_red_flags': list[dict] (severity, category, description, value)
            },
            'risk_analysis': {
                'score': float (0.0-10.0),
                'level': str ('BAIXO'|'MÉDIO'|'ALTO'),
                'rationale': str
            },
            'completeness': {
                'all_fields_present': bool,
                'missing_fields': list[str]
            }
        }
        
        Error response structure:
        {
            'status': 'error',
            'error': str (error type),
            'message': str (detailed error description),
            'invalid_fields': list[str] (if applicable)
        }
    
    Risk Scoring Logic:
        The deterministic risk score (0-10) is calculated based on:
        - Liquidity (0-3 points): Current ratio >= 1.5 (3pts), >= 1.0 (2pts), >= 0.8 (1pt)
        - Financial Health (0-3 points): Positive equity (1.5pts) + Positive net profit (1.5pts)
        - Payment History (0-4 points): No delays (4pts), ≤10% delays (2pts), ≤30% delays (1pt)
        
        Risk levels:
        - BAIXO: score >= 7.0
        - MÉDIO: 4.0 <= score < 7.0
        - ALTO: score < 4.0
        
        Critical flags cap the score at 3.5 (rejection threshold).
    
    Raises:
        No exceptions are raised. All errors are caught and returned in the
        error response format for graceful handling by the agent.
    
    Examples:
        >>> data = '{"empresa": {...}, "duplicata": {...}, "financeiro": {...}}'
        >>> result = extract_financial_data_tool(data)
        >>> result['status']
        'success'
        >>> result['risk_analysis']['score']
        7.5
        >>> result['risk_analysis']['level']
        'BAIXO'
        
        >>> invalid_data = '{"empresa": {}}'
        >>> result = extract_financial_data_tool(invalid_data)
        >>> result['status']
        'error'
        >>> result['error']
        'incomplete_data'
    
    Notes:
        - All monetary values are returned as float in BRL
        - Dates are validated and returned in ISO 8601 format
        - Missing optional fields are set to 0.0 with a warning in completeness
        - CNPJ format is validated (XX.XXX.XXX/XXXX-XX)
        - Current ratio of 0 or infinity is handled gracefully
        - Red flags include liquidity issues (CRITICAL if < 0.8, HIGH if < 1.0)
    """
    
    try:
        data = json.loads(duplicata_json)
        
        required_sections = ['empresa', 'duplicata', 'financeiro']
        missing_sections = [s for s in required_sections if s not in data]
        
        if missing_sections:
            return {
                'status': 'error',
                'error': 'missing_sections',
                'message': f'Required sections missing: {", ".join(missing_sections)}',
                'invalid_fields': missing_sections
            }
        
        empresa = data['empresa']
        if not all(k in empresa for k in ['cnpj', 'razao_social', 'setor']):
            return {
                'status': 'error',
                'error': 'incomplete_empresa_data',
                'message': 'Empresa section must contain cnpj, razao_social, and setor'
            }
        
        cnpj = empresa['cnpj'].replace('.', '').replace('/', '').replace('-', '')
        if len(cnpj) != 14 or not cnpj.isdigit():
            return {
                'status': 'error',
                'error': 'invalid_cnpj',
                'message': f'CNPJ format invalid: {empresa["cnpj"]}'
            }
        
        duplicata = data['duplicata']
        try:
            datetime.fromisoformat(duplicata['vencimento'])
        except (ValueError, TypeError):
             return {
                'status': 'error',
                'error': 'invalid_date_format',
                'message': f'Vencimento must be ISO 8601 format (YYYY-MM-DD). Got: {duplicata.get("vencimento")}'
            }
        if not all(k in duplicata for k in ['valor', 'vencimento']):
            return {
                'status': 'error',
                'error': 'incomplete_duplicata_data',
                'message': 'Duplicata section must contain valor and vencimento'
            }
        
        if duplicata['valor'] <= 0:
            return {
                'status': 'error',
                'error': 'invalid_duplicata_value',
                'message': 'Duplicata valor must be positive'
            }
        
        financeiro = data['financeiro']
        balanco = financeiro.get('balanco_patrimonial', {})
        dre = financeiro.get('dre', {})
        historico = financeiro.get('historico_pagamentos', [])
        
        missing_fields = []
        
        balanco_data = {
            'ativo_circulante': balanco.get('ativo_circulante', 0.0),
            'ativo_nao_circulante': balanco.get('ativo_nao_circulante', 0.0),
            'passivo_circulante': balanco.get('passivo_circulante', 0.0),
            'passivo_nao_circulante': balanco.get('passivo_nao_circulante', 0.0),
            'patrimonio_liquido': balanco.get('patrimonio_liquido', 0.0)
        }
        
        balanco_data['ativo_total'] = (
            balanco_data['ativo_circulante'] + 
            balanco_data['ativo_nao_circulante']
        )
        balanco_data['passivo_total'] = (
            balanco_data['passivo_circulante'] + 
            balanco_data['passivo_nao_circulante']
        )
        
        for field, value in balanco_data.items():
            if field not in ['ativo_total', 'passivo_total'] and value == 0.0:
                if field not in balanco:
                    missing_fields.append(f'balanco.{field}')
        
        dre_data = {
            'receita_bruta': dre.get('receita_bruta', 0.0),
            'receita_liquida': dre.get('receita_liquida', 0.0),
            'lucro_bruto': dre.get('lucro_bruto', 0.0),
            'lucro_operacional': dre.get('lucro_operacional', 0.0),
            'lucro_liquido': dre.get('lucro_liquido', 0.0),
            'ebitda': dre.get('ebitda', 0.0)
        }
        
        for field, value in dre_data.items():
            if value == 0.0 and field not in dre:
                missing_fields.append(f'dre.{field}')
        
        historico_data = {
            'total_operacoes': len(historico),
            'operacoes_pagas': sum(1 for op in historico if op.get('status') == 'PAGO'),
            'atrasos': sum(1 for op in historico if op.get('dias_atraso', 0) > 0),
            'ticket_medio': (
                sum(op.get('valor', 0) for op in historico) / len(historico)
                if historico else 0.0
            )
        }
        
        derived_metrics = {
            'capital_giro': (
                balanco_data['ativo_circulante'] - 
                balanco_data['passivo_circulante']
            ),
            'patrimonio_liquido_tangivel': balanco_data['patrimonio_liquido']
        }
        calculated_red_flags = []

        if balanco_data['passivo_circulante'] > 0:
            liquidez_corrente = balanco_data['ativo_circulante'] / balanco_data['passivo_circulante']
        else:
            liquidez_corrente = 0 if balanco_data['ativo_circulante'] == 0 else 999.0
            
        if liquidez_corrente < 1.0:
            severity = "CRITICAL" if liquidez_corrente < 0.8 else "HIGH"
            calculated_red_flags.append({
                "severity": severity,
                "category": "LIQUIDITY",
                "description": f"Liquidez Corrente baixa ({liquidez_corrente:.2f})",
                "value": liquidez_corrente
            })

        derived_metrics['calculated_red_flags'] = calculated_red_flags
        derived_metrics['liquidez_corrente'] = liquidez_corrente
        
        score = 0.0

        liquidez = derived_metrics.get('liquidez_corrente', 0)
        if liquidez >= 1.5:
            score += 3.0
        elif liquidez >= 1.0:
            score += 2.0
        elif liquidez >= 0.8:
            score += 1.0

        if balanco_data['patrimonio_liquido'] > 0:
            score += 1.5
        if dre_data['lucro_liquido']> 0:
            score += 1.5
        
        total_ops = historico_data['total_operacoes']
        atrasos = historico_data['atrasos']

        if total_ops > 0:
            ratio_atraso = atrasos / total_ops
            if ratio_atraso == 0: 
                score += 4.0
            elif ratio_atraso <= 0.1:
                score += 2.0
            elif ratio_atraso <= 0.3: 
                score += 1.0
        else:
            score += 2.0    
        
        has_critical_flags = any(f['severity'] == 'CRITICAL' for f in derived_metrics.get('calculated_red_flags', []))
        if has_critical_flags:
            score = min(score, 3.5) 

        if score >= 7.0:
            risk_level = "BAIXO"
        elif score >= 4.0:
            risk_level = "MÉDIO"
        else:
            risk_level = "ALTO"

        return {
            'status': 'success',
            'empresa': {
                'cnpj': empresa['cnpj'],
                'razao_social': empresa['razao_social'],
                'setor': empresa['setor']
            },
            'duplicata': {
                'valor': float(duplicata['valor']),
                'vencimento': duplicata['vencimento']
            },
            'balanco': balanco_data,
            'dre': dre_data,
            'historico': historico_data,
            'derived_metrics': derived_metrics,
            'completeness': {
                'all_fields_present': len(missing_fields) == 0,
                'missing_fields': missing_fields
            },
            'risk_analysis': {
                'score': round(score, 1),
                'level': risk_level,
                'rationale': 'Calculated via deterministic policy based on Liquidity, Equity/Profit, and History.'
            }
        }
        
    except json.JSONDecodeError as e:
        return {
            'status': 'error',
            'error': 'invalid_json',
            'message': f'Failed to parse JSON: {str(e)}'
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': 'unexpected_error',
            'message': f'Unexpected error during extraction: {str(e)}'
        }