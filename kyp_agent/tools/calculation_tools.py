from __future__ import annotations
from typing import Dict, Any, List, Optional, Tuple
import logging

# Configure logging for this module
logger = logging.getLogger(__name__)
if not logger.handlers:
    logger.addHandler(logging.NullHandler())

BENCHMARKS = {
    "liquidity": {
        "current_ratio": {"excellent": 2.0, "good": 1.5, "adequate": 1.0},
        "quick_ratio": {"excellent": 1.5, "good": 1.2, "adequate": 1.0},
    },
    "profitability": {
        "roe": {"excellent": 0.20, "good": 0.15, "adequate": 0.10},
        "roa": {"excellent": 0.10, "good": 0.07, "adequate": 0.05},
        "margin_liquida": {"excellent": 0.20, "good": 0.15, "adequate": 0.05},
        "ebitda_margin": {"excellent": 0.25, "good": 0.15, "adequate": 0.08},
    },
    "debt": {
        "debt_ratio": {"excellent": 0.35, "good": 0.50, "adequate": 0.70},
        "equity_multiplier": {"excellent": 1.7, "good": 2.0, "adequate": 2.5},
    },
}


def _safe_get(d: Dict[str, Any], key: str, default: float = 0.0) -> float:
    """Safely extract numeric value from nested dicts (returns float)."""
    try:
        val = d.get(key, default)
        if val is None:
            return float(default)
        return float(val)
    except (ValueError, TypeError):
        raise ValueError(f"Field {key} must be numeric")


def _safe_div(a: float, b: float) -> float:
    """Safe division returning 0.0 on zero-denominator (rounded)."""
    try:
        if b in (0, 0.0, None):
            return 0.0
        return round(a / b, 4)
    except Exception:
        return 0.0


def _interpret(value: float, thresholds: Dict[str, float]) -> str:
    """
    Interpret numeric metric using thresholds mapping.
    Returns one of: "Excelente", "Bom", "Adequado", "Abaixo do esperado"
    """
    try:
        if value >= thresholds.get("excellent", float("inf")):
            return "Excelente"
        if value >= thresholds.get("good", float("inf")):
            return "Bom"
        if value >= thresholds.get("adequate", float("inf")):
            return "Adequado"
        return "Abaixo do esperado"
    except Exception:
        return "Abaixo do esperado"


def _validate_presence(obj: Dict[str, Any], keys: List[str]) -> Optional[Dict[str, Any]]:
    """Return error dict if any key missing, otherwise None."""
    missing = [k for k in keys if k not in obj]
    if missing:
        return {
            "status": "error",
            "error": "missing_fields",
            "message": f"Missing required fields: {', '.join(missing)}",
        }
    return None


# ===========================
# 1) Liquidity
# ===========================
def calculate_liquidity_ratios(extracted_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate core liquidity ratios.
    Required `extracted_data['balanco']` with at least:
      - ativo_circulante
      - passivo_circulante

    Returns a dict with:
    {
      "status": "success" | "error",
      "ratios": {...},
      "interpretation": {...},
      "alerts": [...],
      "strengths": [...]
    }
    """
    logger.info("Starting liquidity ratios calculation")
    try:
        if "balanco" not in extracted_data:
            return {"status": "error", "error": "missing_balanco", "message": "balanco not found"}

        bal = extracted_data["balanco"]
        validation = _validate_presence(bal, ["ativo_circulante", "passivo_circulante"])
        if validation:
            return validation

        ativo_circ = _safe_get(bal, "ativo_circulante")
        passivo_circ = _safe_get(bal, "passivo_circulante")

        if ativo_circ < 0 or passivo_circ < 0:
            logger.error(f"Invalid negative values: ativo_circulante={ativo_circ}, passivo_circulante={passivo_circ}")
            return {"status": "error", "error": "invalid_values", "message": "Assets/liabilities must be non-negative"}

        current_ratio = _safe_div(ativo_circ, passivo_circ)
        # Quick ratio: inventory absent → assume quick_ratio == current_ratio (conservative)
        quick_ratio = current_ratio
        working_capital = round(ativo_circ - passivo_circ, 2)

        ratios = {
            "current_ratio": round(current_ratio, 4),
            "quick_ratio": round(quick_ratio, 4),
            "working_capital": working_capital,
        }

        interpretation = {
            "current_ratio": _interpret(ratios["current_ratio"], BENCHMARKS["liquidity"]["current_ratio"]),
            "quick_ratio": _interpret(ratios["quick_ratio"], BENCHMARKS["liquidity"]["quick_ratio"]),
            "working_capital": "Positivo" if working_capital >= 0 else "Negativo",
        }

        alerts: List[str] = []
        strengths: List[str] = []

        if ratios["current_ratio"] < 1.0:
            alerts.append(f"Liquidez corrente baixa ({ratios['current_ratio']:.2f}).")
        if ratios["current_ratio"] >= BENCHMARKS["liquidity"]["current_ratio"]["excellent"]:
            strengths.append(f"Liquidez corrente excelente ({ratios['current_ratio']:.2f}).")
        if working_capital < 0:
            alerts.append("Capital de giro negativo.")

        logger.info(f"Liquidity calculation successful: current_ratio={ratios['current_ratio']:.2f}, working_capital={working_capital:.2f}")
        logger.debug(f"Liquidity details: {len(alerts)} alerts, {len(strengths)} strengths")
        return {"status": "success", "ratios": ratios, "interpretation": interpretation, "alerts": alerts, "strengths": strengths}
    except ValueError as e:
        logger.exception("Invalid numeric type in calculate_liquidity_ratios")
        return {"status": "error", "error": "invalid_data_type", "message": str(e)}
    except Exception as e:
        logger.exception("Unexpected error in calculate_liquidity_ratios")
        return {"status": "error", "error": "unexpected_error", "message": str(e)}


# ===========================
# 2) Profitability
# ===========================
def calculate_profitability_ratios(extracted_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate core profitability ratios.
    Required: extracted_data['dre'] (receita_liquida, lucro_liquido, lucro_bruto, ebitda)
              extracted_data['balanco'] (ativo_total, patrimonio_liquido)

    Returns structured dict similar to liquidity.
    """
    logger.info("Starting profitability ratios calculation")
    try:
        if "dre" not in extracted_data:
            logger.error("DRE section not found in extracted_data")
            return {"status": "error", "error": "missing_dre", "message": "dre not found"}
        if "balanco" not in extracted_data:
            logger.error("Balanco section not found in extracted_data")
            return {"status": "error", "error": "missing_balanco", "message": "balanco not found"}

        dre = extracted_data["dre"]
        bal = extracted_data["balanco"]

        # safe extraction with defaults
        receita_liq = _safe_get(dre, "receita_liquida")
        lucro_liq = _safe_get(dre, "lucro_liquido")
        lucro_bruto = _safe_get(dre, "lucro_bruto")
        ebitda = _safe_get(dre, "ebitda")

        ativo_total = _safe_get(bal, "ativo_total")
        patrimonio_liq = _safe_get(bal, "patrimonio_liquido")

        roe = _safe_div(lucro_liq, patrimonio_liq) if patrimonio_liq > 0 else 0.0
        roa = _safe_div(lucro_liq, ativo_total) if ativo_total > 0 else 0.0
        margem_bruta = _safe_div(lucro_bruto, receita_liq) if receita_liq > 0 else 0.0
        margem_liq = _safe_div(lucro_liq, receita_liq) if receita_liq > 0 else 0.0
        ebitda_margin = _safe_div(ebitda, receita_liq) if receita_liq > 0 else 0.0

        ratios = {
            "roe": round(roe, 4),
            "roa": round(roa, 4),
            "margem_bruta": round(margem_bruta, 4),
            "margem_liquida": round(margem_liq, 4),
            "ebitda_margin": round(ebitda_margin, 4),
        }

        interpretation = {
            "roe": _interpret(ratios["roe"], BENCHMARKS["profitability"]["roe"]),
            "roa": _interpret(ratios["roa"], BENCHMARKS["profitability"]["roa"]),
            "margem_liquida": _interpret(ratios["margem_liquida"], BENCHMARKS["profitability"]["margin_liquida"]),
            "ebitda_margin": _interpret(ratios["ebitda_margin"], BENCHMARKS["profitability"]["ebitda_margin"]),
        }

        alerts: List[str] = []
        strengths: List[str] = []

        if ratios["roe"] < 0.10:
            alerts.append(f"ROE baixo ({ratios['roe']*100:.1f}%).")
        elif ratios["roe"] >= BENCHMARKS["profitability"]["roe"]["excellent"]:
            strengths.append(f"ROE forte ({ratios['roe']*100:.1f}%).")

        if ratios["margem_liquida"] <= 0:
            alerts.append("Margem líquida negativa ou zero.")

        if ratios["ebitda_margin"] >= BENCHMARKS["profitability"]["ebitda_margin"]["excellent"]:
            strengths.append(f"EBITDA margin forte ({ratios['ebitda_margin']*100:.1f}%).")

        logger.info(f"Profitability calculation successful: ROE={ratios['roe']*100:.1f}%, ROA={ratios['roa']*100:.1f}%")
        logger.debug(f"Profitability details: {len(alerts)} alerts, {len(strengths)} strengths")
        return {"status": "success", "ratios": ratios, "interpretation": interpretation, "alerts": alerts, "strengths": strengths}
    except ValueError as e:
        logger.exception("Invalid numeric type in calculate_profitability_ratios")
        return {"status": "error", "error": "invalid_data_type", "message": str(e)}
    except Exception as e:
        logger.exception("Unexpected error in calculate_profitability_ratios")
        return {"status": "error", "error": "unexpected_error", "message": str(e)}


# ===========================
# 3) Debt / Solvency
# ===========================
def calculate_debt_ratios(extracted_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate debt-related ratios.
    Requires: extracted_data['balanco'] with passivo_total, passivo_circulante, ativo_total, patrimonio_liquido
    """
    logger.info("Starting debt ratios calculation")
    try:
        if "balanco" not in extracted_data:
            return {"status": "error", "error": "missing_balanco", "message": "balanco not found"}

        bal = extracted_data["balanco"]

        passivo_total = _safe_get(bal, "passivo_total")
        passivo_circ = _safe_get(bal, "passivo_circulante")
        ativo_total = _safe_get(bal, "ativo_total")
        patrimonio_liq = _safe_get(bal, "patrimonio_liquido")

        debt_ratio = _safe_div(passivo_total, ativo_total) if ativo_total > 0 else 0.0

        # debt_to_equity = passivo / patrimonio (can be inf if equity <=0)
        if patrimonio_liq <= 0:
            debt_to_equity = float("inf") if passivo_total > 0 else 0.0
        else:
            debt_to_equity = _safe_div(passivo_total, patrimonio_liq)

        # equity multiplier = assets / equity (if equity <=0 => inf representation 9999)
        if patrimonio_liq <= 0:
            equity_multiplier = float("inf") if passivo_total > 0 else 0.0
        else:
            equity_multiplier = _safe_div(ativo_total, patrimonio_liq)

        debt_composition = _safe_div(passivo_circ, passivo_total) if passivo_total > 0 else 0.0

        estimated_interest = passivo_total * 0.10  # conservative estimate if interest missing
        # interest coverage uses lucro_operacional if present, else use lucro_liquido
        dre = extracted_data.get("dre", {})
        lucro_operacional = _safe_get(dre, "lucro_operacional", _safe_get(dre, "lucro_liquido", 0.0))
        if estimated_interest > 0:
            interest_coverage = _safe_div(lucro_operacional, estimated_interest)
        else:
            interest_coverage = float("inf") if lucro_operacional > 0 else 0.0

        # format ratios
        ratios = {
            "debt_ratio": round(debt_ratio, 4),
            "debt_to_equity": (round(debt_to_equity, 2) if debt_to_equity != float("inf") else "inf"),
            "equity_multiplier": (round(equity_multiplier, 2) if equity_multiplier != float("inf") else "inf"),
            "debt_composition": round(debt_composition, 4),
            "interest_coverage": (round(interest_coverage, 2) if interest_coverage != float("inf") else "inf"),
        }

        # debt_to_equity interpretation: HIGHER = MORE debt relative to equity = MORE risk
        if debt_to_equity == float("inf"):
            dte_interp = "CRÍTICO - Patrimônio líquido zero ou negativo"
        elif debt_to_equity > 2.0:
            dte_interp = "Alto - Endividamento elevado em relação ao patrimônio"
        elif debt_to_equity > 1.0:
            dte_interp = "Moderado - Dívida superior ao patrimônio"
        elif debt_to_equity > 0.5:
            dte_interp = "Adequado - Dívida controlada"
        else:
            dte_interp = "Excelente - Baixo endividamento"

        # equity_multiplier interpretation: HIGHER values = MORE leverage = MORE risk
        if equity_multiplier == float("inf"):
            em_interp = "CRÍTICO - Patrimônio líquido zero ou negativo"
        elif equity_multiplier > 3.0:
            em_interp = "Alto - Alavancagem excessiva"
        elif equity_multiplier > 2.5:
            em_interp = "Moderado - Alavancagem acima da média"
        elif equity_multiplier > 2.0:
            em_interp = "Adequado - Alavancagem dentro do esperado"
        else:
            em_interp = "Excelente - Baixa alavancagem"

        interpretation = {
            "debt_ratio": _interpret(debt_ratio, BENCHMARKS["debt"]["debt_ratio"]),
            "debt_to_equity": dte_interp,
            "equity_multiplier": em_interp,
            "debt_composition": ("Risco de liquidez" if debt_composition > 0.6 else "Normal"),
            "interest_coverage": ("Excelente" if interest_coverage > 5 or interest_coverage == float("inf") else ("Adequado" if interest_coverage >= 2 else "Risco")),
        }

        alerts: List[str] = []
        strengths: List[str] = []

        if equity_multiplier == float("inf"):
            alerts.append("Patrimônio líquido zero ou negativo - atenção para solvência.")
        elif (isinstance(equity_multiplier, float) and equity_multiplier > BENCHMARKS["debt"]["equity_multiplier"]["adequate"]):
            alerts.append(f"Equity multiplier elevado ({equity_multiplier:.2f}) - alavancagem alta.")

        if debt_ratio > BENCHMARKS["debt"]["debt_ratio"]["adequate"]:
            alerts.append(f"Endividamento elevado ({debt_ratio*100:.1f}% dos ativos).")
        else:
            strengths.append("Endividamento dentro do esperado para o setor.")

        if debt_composition > 0.6:
            alerts.append(f"Concentração em curto prazo ({debt_composition*100:.1f}%).")

        if interest_coverage != float("inf") and interest_coverage < 2:
            alerts.append(f"Baixa cobertura de juros ({interest_coverage:.2f}x).")
        elif interest_coverage > 5 or interest_coverage == float("inf"):
            strengths.append("Boa capacidade de cobertura de juros.")

        logger.info(f"Debt calculation successful: debt_ratio={debt_ratio*100:.1f}%, equity_multiplier={equity_multiplier if equity_multiplier != float('inf') else 'inf'}")
        logger.debug(f"Debt details: {len(alerts)} alerts, {len(strengths)} strengths")
        return {"status": "success", "ratios": ratios, "interpretation": interpretation, "alerts": alerts, "strengths": strengths}
    except ValueError as e:
        logger.exception("Invalid numeric type in calculate_debt_ratios")
        return {"status": "error", "error": "invalid_data_type", "message": str(e)}
    except Exception as e:
        logger.exception("Unexpected error in calculate_debt_ratios")
        return {"status": "error", "error": "unexpected_error", "message": str(e)}


# ===========================
# 4) Benchmarks comparison
# ===========================
def compare_with_benchmarks(liquidity: Dict[str, Any], profitability: Dict[str, Any], debt: Dict[str, Any], sector: str) -> Dict[str, Any]:
    """
    Compare company ratios with sector benchmarks.
    Returns:
    {
      "status": "success"|"error",
      "sector": str,
      "benchmarks": { ...comparisons... },
      "overall_assessment": str,
      "competitive_position": str,
      "metrics_summary": {...}
    }
    """
    logger.info(f"Starting benchmark comparison for sector: {sector}")
    try:
        # Basic validation
        for name, obj in (("liquidity", liquidity), ("profitability", profitability), ("debt", debt)):
            if obj.get("status") != "success":
                return {"status": "error", "error": f"invalid_{name}_data", "message": f"{name} data must have status success"}

        # Use a concise mapping of company => sector comparison using available ratios
        # If sector unknown, still return a generic comparison (sector optional)
        sector_bench = BENCHMARKS  # we keep minimal sector logic; expandable

        # Build comparisons (company value, sector reference (where possible), simple status)
        comparisons = {}
        # current_ratio
        try:
            comp_current = liquidity["ratios"]["current_ratio"]
            compar = {
                "company": comp_current,
                "sector_avg": sector_bench["liquidity"]["current_ratio"]["good"],
                "status": _interpret(comp_current, sector_bench["liquidity"]["current_ratio"])
            }
            comparisons["current_ratio"] = compar
        except Exception:
            pass

        # profitability checks
        for key in ("roe", "roa", "margem_liquida", "ebitda_margin"):
            if key in profitability["ratios"]:
                val = profitability["ratios"][key]
                sector_ref = sector_bench["profitability"].get(key, {})
                comparisons[key] = {"company": val, "sector_avg": sector_ref.get("good", 0.0), "status": _interpret(val, sector_ref)}

        # debt checks
        try:
            debt_val = debt["ratios"]["debt_ratio"]
            comparisons["debt_to_assets"] = {"company": debt_val, "sector_avg": sector_bench["debt"]["debt_ratio"]["good"], "status": _interpret(debt_val, sector_bench["debt"]["debt_ratio"])}
        except Exception:
            pass

        # Score heuristics: count "Abaixo do esperado" occurrences
        statuses = [c.get("status") for c in comparisons.values() if isinstance(c, dict)]
        below_count = sum(1 for s in statuses if s == "Abaixo do esperado")
        excellent_count = sum(1 for s in statuses if s == "Excelente")

        if excellent_count >= 3:
            overall = "above_average"
            competitive = f"A empresa apresenta performance superior ao setor ({sector})."
        elif below_count >= 3:
            overall = "below_average"
            competitive = f"A empresa apresenta performance abaixo da média do setor ({sector})."
        else:
            overall = "average"
            competitive = f"A empresa está alinhada com a média do setor ({sector})."

        metrics_summary = {
            "total_metrics": len(comparisons),
            "above_average": excellent_count,
            "below_average": below_count,
            "average": len(comparisons) - (excellent_count + below_count),
        }

        return {
            "status": "success",
            "sector": sector,
            "benchmarks": comparisons,
            "overall_assessment": overall,
            "competitive_position": competitive,
            "metrics_summary": metrics_summary,
        }
        logger.info(f"Benchmark comparison successful: overall_assessment={overall}, sector={sector}")
        logger.debug(f"Metrics summary: {metrics_summary}")
        return result
    except Exception as e:
        logger.exception("Unexpected error in compare_with_benchmarks")
        return {"status": "error", "error": "unexpected_error", "message": str(e)}


# ===========================
# 5) Financial health scoring and summary
# ===========================
def calculate_financial_health_score(liquidity: Dict[str, Any], profitability: Dict[str, Any], debt: Dict[str, Any]) -> float:
    """
    Weighted scoring (0-10) combining liquidity, profitability and debt signals.
    Weights:
      - Liquidity: 30%
      - Profitability: 40%
      - Debt: 30%
    """
    try:
        # Liquidity subscore (normalize current_ratio into 0-10 scale capped)
        cr = liquidity["ratios"].get("current_ratio", 0.0)
        liq_score = min(max(cr / 2.5 * 10, 0), 10)  # 2.5 -> 10 points

        roe = profitability["ratios"].get("roe", 0.0)
        margin = profitability["ratios"].get("margem_liquida", 0.0)
        # Profitability combined (simple weighted)
        prof_score = min(max((roe * 10) * 0.6 + (margin * 10) * 0.4, 0), 10)

        dr = debt["ratios"].get("debt_ratio", 1.0)
        # Debt: lower is better -> transform to score 0-10
        if dr <= 0.3:
            debt_score = 10
        elif dr <= 0.5:
            debt_score = 8
        elif dr <= 0.7:
            debt_score = 5
        else:
            debt_score = 2

        weighted = (liq_score * 0.3) + (prof_score * 0.4) + (debt_score * 0.3)
        return round(min(max(weighted, 0), 10), 2)
    except Exception as e:
        logger.exception("Error in calculate_financial_health_score")
        return 0.0


def generate_financial_summary(liquidity: Dict[str, Any], profitability: Dict[str, Any], debt: Dict[str, Any], benchmark: Dict[str, Any], score: float) -> str:
    """
    Build a concise 2-3 sentence executive summary in PT-BR.
    """
    try:
        liq_interp = liquidity["interpretation"].get("current_ratio", "N/A")
        roe_interp = profitability["interpretation"].get("roe", "N/A")
        competitive = benchmark.get("competitive_position", "")

        # Compose 2-3 sentence summary
        sentences: List[str] = []
        sentences.append(
            f"A empresa apresenta saúde financeira geral de {score:.1f}/10, com liquidez classificada como {liq_interp}."
        )

        sentences.append(
            f"A rentabilidade é avaliada como {roe_interp} e a posição competitiva: {competitive}."
        )

        # add top alerts if any
        top_alerts = []
        for src in (liquidity, profitability, debt):
            if src.get("alerts"):
                top_alerts.extend(src["alerts"][:1])
        if top_alerts:
            sentences.append("Pontos de atenção: " + " ".join(top_alerts))

        return " ".join(sentences)
    except Exception as e:
        logger.exception("Error in generate_financial_summary")
        return "Resumo indisponível devido a erro interno."


# ===========================
# 6) Full pipeline
# ===========================
def calculate_all_financial_ratios(extracted_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Full pipeline that calculates liquidity, profitability, debt, benchmarks,
    score and summary. Returns a unified response that your ADK agent can consume.
    """
    try:
        # validation
        if not isinstance(extracted_data, dict):
            return {"status": "error", "error": "invalid_input", "message": "extracted_data must be a dict"}

        # Step 1 - liquidity
        liquidity = calculate_liquidity_ratios(extracted_data)
        if liquidity.get("status") != "success":
            return {"status": "error", "error": "liquidity_failed", "message": liquidity.get("message", "liquidity error")}

        # Step 2 - profitability
        profitability = calculate_profitability_ratios(extracted_data)
        if profitability.get("status") != "success":
            return {"status": "error", "error": "profitability_failed", "message": profitability.get("message", "profitability error")}

        # Step 3 - debt
        debt = calculate_debt_ratios(extracted_data)
        if debt.get("status") != "success":
            return {"status": "error", "error": "debt_failed", "message": debt.get("message", "debt error")}

        # Step 4 - benchmark comparison
        sector = extracted_data.get("empresa", {}).get("setor", "Desconhecido")
        benchmark = compare_with_benchmarks(liquidity, profitability, debt, sector)
        if benchmark.get("status") != "success":
            return {"status": "error", "error": "benchmark_failed", "message": benchmark.get("message", "benchmark error")}

        # Step 5 - health score
        score = calculate_financial_health_score(liquidity, profitability, debt)

        # Step 6 - summary
        summary = generate_financial_summary(liquidity, profitability, debt, benchmark, score)

        return {
            "status": "success",
            "liquidity": liquidity,
            "profitability": profitability,
            "debt": debt,
            "benchmark_comparison": benchmark,
            "financial_health_score": score,
            "summary": summary,
        }
    except Exception as e:
        logger.exception("Unexpected error in calculate_all_financial_ratios pipeline")
        return {"status": "error", "error": "unexpected_error", "message": str(e)}
