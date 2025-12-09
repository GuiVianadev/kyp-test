import logging

logger = logging.getLogger(__name__)
if not logger.handlers:
    logger.addHandler(logging.NullHandler())


def generate_complete_report(
    credit_analysis: dict,
    financial_ratios: dict
) -> dict:
    """Generate complete credit analysis report in Markdown format.
    
    Creates a comprehensive, professional credit report combining risk analysis,
    financial ratios, and final recommendation in a single formatted document.
    
    Args:
        credit_analysis: Complete output from credit_analyzer agent containing:
                        - status, risk_level, risk_score
                        - extracted_data (empresa, duplicata, balanco, dre)
                        - red_flags, positive_points
                        - preliminary_recommendation, critical_notes
        
        financial_ratios: Complete output from ratio_calculator agent containing:
                         - status
                         - liquidity (ratios, interpretation, alerts, strengths)
                         - profitability (ratios, interpretation)
                         - debt (ratios, interpretation)
                         - benchmark_comparison
                         - financial_health_score, summary
    
    Returns:
        Dictionary with report generation status and markdown content:
        {
            'status': 'success' | 'error',
            'report': str (complete markdown report),
            'final_decision': 'APROVAR' | 'APROVAR COM RESSALVAS' | 'REVISAR' | 'NEGAR',
            'metadata': {
                'generated_at': str (ISO datetime),
                'report_length': int (character count),
                'sections': int (number of sections)
            }
        }
        
        Error response:
        {
            'status': 'error',
            'error': str (error type),
            'message': str (detailed error description)
        }
    
    Example:
        >>> report = generate_complete_report(credit_data, ratio_data)
        >>> print(report['report'][:100])
        # RELATÓRIO DE ANÁLISE DE CRÉDITO
        # DUPLICATA ESCRITURAL
        ...
        >>> report['final_decision']
        'APROVAR'
    """
    from datetime import datetime
    
    try:
 
        if credit_analysis.get('status') != 'success':
            return {
                'status': 'error',
                'error': 'invalid_credit_analysis',
                'message': 'credit_analysis must have success status'
            }
        
        if financial_ratios.get('status') != 'success':
            return {
                'status': 'error',
                'error': 'invalid_financial_ratios',
                'message': 'financial_ratios must have success status'
            }
  
        empresa = credit_analysis['extracted_data']['empresa']
        duplicata = credit_analysis['extracted_data']['duplicata']
        
 
        risk_level = credit_analysis['risk_level']
        risk_score = credit_analysis['risk_score']
        red_flags = credit_analysis.get('red_flags', [])
        positive_points = credit_analysis.get('positive_points', [])
        critical_notes = credit_analysis.get('critical_notes', '')
        
        liquidity = financial_ratios['liquidity']
        profitability = financial_ratios['profitability']
        debt = financial_ratios['debt']
        benchmark = financial_ratios['benchmark_comparison']
        health_score = financial_ratios['financial_health_score']
        summary = financial_ratios['summary']
        

        now = datetime.now()
        data_analise = now.strftime('%d/%m/%Y')
        timestamp = now.isoformat()
        
        
        if risk_score >= 7.0 and health_score >= 8.0:
            decision = 'APROVAR'
            decision_emoji = '✅'
            taxa_sugerida = 'CDI + 2.5% a.a.'
            prazo_sugerido = '180 dias'
            garantias = 'Duplicata escritural'
            monitoramento = 'semestral'
        elif risk_score >= 5.0 and health_score >= 6.0:
            decision = 'APROVAR COM RESSALVAS'
            decision_emoji = '⚠️'
            taxa_sugerida = 'CDI + 4.0% a.a.'
            prazo_sugerido = '120 dias'
            garantias = 'Duplicata escritural + Aval dos sócios'
            monitoramento = 'trimestral'
        elif risk_score >= 4.0:
            decision = 'REVISAR'
            decision_emoji = '🔄'
            taxa_sugerida = 'A definir após revisão'
            prazo_sugerido = 'A definir'
            garantias = 'A definir - considerar garantias reais'
            monitoramento = 'N/A'
        else:
            decision = 'NEGAR'
            decision_emoji = '❌'
            taxa_sugerida = 'N/A'
            prazo_sugerido = 'N/A'
            garantias = 'N/A'
            monitoramento = 'N/A'
        
        
        report = f"""# RELATÓRIO DE ANÁLISE DE CRÉDITO
# DUPLICATA ESCRITURAL

---

## 1. RESUMO EXECUTIVO

**Empresa:** {empresa['razao_social']}  
**CNPJ:** {empresa['cnpj']}  
**Setor:** {empresa['setor']}  
**Valor da Duplicata:** R$ {duplicata['valor']:,.2f}  
**Vencimento:** {duplicata['vencimento']}  
**Data de Análise:** {data_analise}

---

### Síntese da Avaliação

**Nível de Risco:** {risk_level} (Score: {risk_score}/10)  
**Saúde Financeira:** {health_score}/10  
**Recomendação Preliminar:** {credit_analysis['preliminary_recommendation']}

{summary}

---

## 2. ANÁLISE DE RISCO

**Classificação de Risco:** {risk_level}  
**Score de Risco:** {risk_score}/10

### Pontos de Atenção

"""
        
        if red_flags:
            for i, flag in enumerate(red_flags, 1):
                severity_emoji = {
                    'CRITICAL': '🔴',
                    'HIGH': '🟠',
                    'MEDIUM': '🟡',
                    'LOW': '🟢'
                }.get(flag.get('severity', 'MEDIUM'), '⚪')
                
                report += f"{i}. {severity_emoji} **{flag.get('category', 'N/A')}** ({flag.get('severity', 'N/A')})\n"
                report += f"   - {flag.get('description', 'N/A')}\n"
                report += f"   - *Impacto:* {flag.get('impact', 'N/A')}\n\n"
        else:
            report += "Nenhum ponto de atenção crítico identificado.\n\n"
        
        report += "### Pontos Positivos\n\n"
        

        if positive_points:
            for i, point in enumerate(positive_points, 1):
                report += f"{i}. ✅ **{point.get('category', 'N/A')}**\n"
                report += f"   - {point.get('description', 'N/A')}\n"
                report += f"   - *Impacto:* {point.get('impact', 'N/A')}\n\n"
        
        report += f"### Notas do Analista\n\n{critical_notes}\n\n"
        
        report += "---\n\n"
        
        
        report += """## 3. INDICADORES FINANCEIROS

### 3.1 Liquidez

| Indicador | Valor | Interpretação |
|-----------|-------|---------------|
"""
        
        liq_ratios = liquidity['ratios']
        liq_interp = liquidity['interpretation']
        
        report += f"| Liquidez Corrente | {liq_ratios['current_ratio']:.2f} | {liq_interp['current_ratio']} |\n"
        report += f"| Liquidez Seca | {liq_ratios['quick_ratio']:.2f} | {liq_interp['quick_ratio']} |\n"
        report += f"| Capital de Giro | R$ {liq_ratios['working_capital']:,.2f} | {liq_interp['working_capital']} |\n\n"
        

        if liquidity.get('strengths'):
            report += "**Destaques:**\n"
            for strength in liquidity['strengths']:
                report += f"- {strength}\n"
            report += "\n"
        
        if liquidity.get('alerts'):
            report += "**Alertas:**\n"
            for alert in liquidity['alerts']:
                report += f"- {alert}\n"
            report += "\n"
        
        report += "### 3.2 Rentabilidade\n\n"
        report += "| Indicador | Empresa | Setor | Status |\n"
        report += "|-----------|---------|-------|--------|\n"
        
        prof_ratios = profitability['ratios']
        bench_data = benchmark['benchmarks']
        
     
        def get_status_emoji(status):
            return {
                'well_above_average': '🟢🟢',
                'above_average': '🟢',
                'average': '🟡',
                'below_average': '🟠',
                'well_below_average': '🔴',
                'critical': '🔴🔴'
            }.get(status, '⚪')
        
    
        roe = prof_ratios['roe']
        roe_bench = bench_data.get('roe', {})
        report += f"| ROE | {roe*100:.1f}% | {roe_bench.get('sector_avg', 0)*100:.1f}% | {get_status_emoji(roe_bench.get('status', 'average'))} |\n"
        
    
        roa = prof_ratios['roa']
        roa_bench = bench_data.get('roa', {})
        report += f"| ROA | {roa*100:.1f}% | {roa_bench.get('sector_avg', 0)*100:.1f}% | {get_status_emoji(roa_bench.get('status', 'average'))} |\n"
        
     
        ml = prof_ratios['margem_liquida']
        ml_bench = bench_data.get('margem_liquida', {})
        report += f"| Margem Líquida | {ml*100:.1f}% | {ml_bench.get('sector_avg', 0)*100:.1f}% | {get_status_emoji(ml_bench.get('status', 'average'))} |\n"
        
    
        mb = prof_ratios['margem_bruta']
        report += f"| Margem Bruta | {mb*100:.1f}% | - | - |\n"
        
  
        ebitda = prof_ratios['ebitda_margin']
        ebitda_bench = bench_data.get('ebitda_margin', {})
        report += f"| EBITDA Margin | {ebitda*100:.1f}% | {ebitda_bench.get('sector_avg', 0)*100:.1f}% | {get_status_emoji(ebitda_bench.get('status', 'average'))} |\n\n"
        
        report += "### 3.3 Endividamento\n\n"
        report += "| Indicador | Valor | Interpretação |\n"
        report += "|-----------|-------|---------------|\n"
        
        debt_ratios = debt['ratios']
        debt_interp = debt['interpretation']
        
     
        dte = debt_ratios['debt_to_equity']
        dte_display = f"{dte:.2f}" if dte != 'inf' else 'N/A'
        report += f"| Dívida/Patrimônio | {dte_display} | {debt_interp['debt_to_equity']} |\n"
        
       
        dta = debt_ratios['debt_ratio']
        report += f"| Endividamento Geral | {dta*100:.1f}% | {debt_interp['debt_ratio']} |\n"
        
     
        dc = debt_ratios['debt_composition']
        report += f"| Composição Curto Prazo | {dc*100:.1f}% | {debt_interp['debt_composition']} |\n"
        
    
        ic = debt_ratios['interest_coverage']
        ic_display = f"{ic:.1f}x" if ic != 'inf' else '∞'
        report += f"| Cobertura de Juros | {ic_display} | {debt_interp['interest_coverage']} |\n\n"
        
   
        if debt.get('strengths'):
            report += "**Destaques:**\n"
            for strength in debt['strengths']:
                report += f"- {strength}\n"
            report += "\n"
        
        if debt.get('alerts'):
            report += "**Alertas:**\n"
            for alert in debt['alerts']:
                report += f"- {alert}\n"
            report += "\n"
        

        report += f"""### 3.4 Comparação com Setor

**Setor:** {benchmark['sector']}  
**Avaliação Geral:** {benchmark['overall_assessment'].replace('_', ' ').title()}

{benchmark['competitive_position']}

---

"""
        
        report += f"""## 4. RECOMENDAÇÃO FINAL

### {decision_emoji} **DECISÃO: {decision}**

"""
        
        if decision in ['APROVAR', 'APROVAR COM RESSALVAS']:
            report += f"""**Valor Aprovado:** R$ {duplicata['valor']:,.2f}

### Condições Sugeridas

- **Taxa de Juros:** {taxa_sugerida}
- **Prazo:** {prazo_sugerido}
- **Garantias:** {garantias}

### Plano de Monitoramento

"""
            if decision == 'APROVAR':
                report += f"""- Revisão {monitoramento} dos indicadores financeiros
- Acompanhamento trimestral do fluxo de caixa
- Verificação de manutenção dos covenants:
  - Liquidez corrente > 1.5
  - Endividamento geral < 50%
  - EBITDA positivo
"""
            else: 
                report += f"""- **Revisão {monitoramento}** dos indicadores financeiros (OBRIGATÓRIA)
- **Acompanhamento mensal** do fluxo de caixa
- Verificação rigorosa de manutenção dos covenants:
  - Liquidez corrente > 1.2
  - Endividamento geral < 60%
  - Margem EBITDA > 10%
- Alertas automáticos para atrasos > 5 dias
- Reavaliação em 90 dias
"""
        
        elif decision == 'REVISAR':
            report += """### Pontos a Revisar

- Análise detalhada do fluxo de caixa projetado para os próximos 12 meses
- Validação das garantias disponíveis e sua liquidez
- Avaliação de relacionamento bancário histórico
- Possibilidade de co-obrigados ou avalistas adicionais
- Visita técnica às instalações (se aplicável)

### Próximos Passos

1. Solicitar documentação adicional ao cliente:
   - Demonstrações financeiras auditadas
   - Fluxo de caixa projetado
   - Contratos com principais clientes
2. Realizar análise complementar de mercado
3. Submeter à reunião do comitê de crédito
4. **Decisão final em até 5 dias úteis**
"""
        
        else:
            report += f"""### Justificativa da Negativa

Com base na análise realizada, a operação apresenta **risco elevado** (Score: {risk_score}/10) 
que não se enquadra nas políticas de crédito vigentes da instituição.

Os principais fatores limitantes são:
"""
            if red_flags:
                for flag in red_flags[:3]: 
                    report += f"- {flag.get('description', 'N/A')}\n"
            
            report += """
### Recomendação ao Cliente

Sugerimos que a empresa trabalhe nos seguintes pontos antes de uma nova solicitação:

1. Melhore os indicadores de liquidez e rentabilidade
2. Reduza o nível de endividamento, especialmente de curto prazo
3. Estabeleça histórico de pagamentos positivo por pelo menos 6 meses
4. Considere apresentar garantias reais adicionais

**Nova análise poderá ser solicitada após 6 meses**, desde que demonstrada evolução nos pontos acima.
"""
        
        report += f"""
---

## Assinaturas e Aprovações

**Analista Responsável:** Sistema KYP Credit Analysis (Automatizado)  
**Data de Geração:** {data_analise}  
**Validade da Análise:** 30 dias  

---

*Relatório gerado automaticamente pelo Sistema KYP Credit Analysis v1.0*  
*Timestamp: {timestamp}*  
*Documento confidencial - Uso restrito ao comitê de crédito*

---

### Disclaimer

Este relatório foi gerado por sistema automatizado de análise de crédito utilizando
Inteligência Artificial e dados fornecidos pelo solicitante. A decisão final deve
considerar fatores qualitativos adicionais e estar sujeita à aprovação do comitê
de crédito da instituição.
"""

        
        metadata = {
            'generated_at': timestamp,
            'report_length': len(report),
            'sections': 4,
            'empresa': empresa['razao_social'],
            'cnpj': empresa['cnpj'],
            'valor_duplicata': duplicata['valor']
        }
        
        return {
            'status': 'success',
            'report': report,
            'final_decision': decision,
            'metadata': metadata
        }
        
    except KeyError as e:
        return {
            'status': 'error',
            'error': 'missing_required_field',
            'message': f'Required field missing in input data: {str(e)}'
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': 'unexpected_error',
            'message': f'Failed to generate report: {str(e)}'
        }