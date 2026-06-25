"""
build_chart_disposition.py — Machine-verifiable disposition of all 66 original
Excel charts (NEXT_PHASE Loop 13).

Per CHART_MIGRATION_PLAN.md, each original chart gets a status:
  retained | merged_into | rebuilt_as | deleted_with_reason

Status rules:
  - retained: original content kept as a primary chart (target_chart_ids set)
  - merged_into: original absorbed into a unified chart (e.g. seasonality selector)
  - rebuilt_as: analysis question kept but redrawn (e.g. floating range, scatter)
  - deleted_with_reason: removed (duplicate, untitled, layout-only)
"""
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Disposition table — derived from CHART_MIGRATION_PLAN.md section 四.
# Format: excel_chart_id -> {status, target_chart_ids, reason}
DISPOSITIONS = {
    # ── 3.即远期 (7) ──
    "3.即远期#01": ("retained", ["fx_fwd_total_supply"], "总供求柱+12MMA线,主保留"),
    "3.即远期#02": ("retained", ["fx_fwd_bank_own"], "两类贡献堆叠柱+总量线"),
    "3.即远期#03": ("deleted_with_reason", [], "与#04/#01高度重复"),
    "3.即远期#04": ("retained", ["fx_fwd_total_supply"], "银行发生额+衍生品签约,主保留"),
    "3.即远期#05": ("retained", ["fx_fwd_spot_breakdown"], "桥接式分解柱,主保留"),
    "3.即远期#06": ("retained", ["fx_fwd_deriv_components"], "远期+期权三项贡献柱,主保留"),
    "3.即远期#07": ("retained", ["fx_fwd_deriv_vs_usdcny"], "双轴Flow+USDCNY,次保留"),
    # ── 3.代客即期 (10) ──
    "3.代客即期#01": ("retained", ["fx_cspot_current_financial"], "经常/金融月度柱+6MMA,主保留"),
    "3.代客即期#02": ("retained", ["fx_cspot_full_decomp"], "六类堆叠柱,主保留"),
    "3.代客即期#03": ("merged_into", ["fx_cspot_full_decomp"], "经常账户分解,并入完整分解图"),
    "3.代客即期#04": ("merged_into", ["fx_cspot_full_decomp"], "金融账户分解,并入完整分解图"),
    "3.代客即期#05": ("retained", ["fx_cspot_current_financial"], "经常/金融+总量线,主保留"),
    "3.代客即期#06": ("merged_into", ["fx_cspot_seasonality"], "货物贸易季节性,并入季节性选择器"),
    "3.代客即期#07": ("merged_into", ["fx_cspot_seasonality"], "服务贸易季节性,并入选择器"),
    "3.代客即期#08": ("merged_into", ["fx_cspot_seasonality"], "收益转移季节性,并入选择器"),
    "3.代客即期#09": ("merged_into", ["fx_cspot_seasonality"], "直接投资季节性,并入选择器"),
    "3.代客即期#10": ("deleted_with_reason", [], "与#02重复"),
    # ── 3.涉外收付 (11) ──
    "3.涉外收付#01": ("retained", ["fx_cross_full_decomp"], "六类堆叠柱,主保留"),
    "3.涉外收付#02": ("retained", ["fx_cross_currency_decomp"], "币种堆叠柱,主保留"),
    "3.涉外收付#03": ("retained", ["fx_cross_full_decomp"], "经常/金融双线突出零轴"),
    "3.涉外收付#04": ("retained", ["fx_cross_cny_usd_share"], "占比线0-100%轴,主保留"),
    "3.涉外收付#05": ("merged_into", ["fx_cross_seasonality"], "货物贸易季节性,并入选择器"),
    "3.涉外收付#06": ("merged_into", ["fx_cross_seasonality"], "服务贸易季节性,并入选择器"),
    "3.涉外收付#07": ("merged_into", ["fx_cross_seasonality"], "收益转移季节性,并入选择器"),
    "3.涉外收付#08": ("merged_into", ["fx_cross_seasonality"], "直接投资季节性,并入选择器"),
    "3.涉外收付#09": ("deleted_with_reason", [], "与#03重复"),
    "3.涉外收付#10": ("merged_into", ["fx_cross_full_decomp"], "金融账户分解,并入完整分解图"),
    "3.涉外收付#11": ("merged_into", ["fx_cross_full_decomp"], "经常账户分解,并入完整分解图"),
    # ── 3.货物贸易 (10) ──
    "3.货物贸易#01": ("rebuilt_as", ["trade_goods_unsettled_position"], "浮动区间条+当前点,重做"),
    "3.货物贸易#02": ("retained", ["trade_goods_ttm_panel"], "多序列TTM线,先修TTM为rolling sum"),
    "3.货物贸易#03": ("retained", ["trade_goods_percentile"], "两条percentile线0-100%,次保留"),
    "3.货物贸易#04": ("retained", ["trade_goods_unsettled_position"], "两条余额线+零轴,主保留"),
    "3.货物贸易#05": ("merged_into", ["trade_goods_seasonality"], "贸易顺差季节性,并入选择器"),
    "3.货物贸易#06": ("merged_into", ["trade_goods_seasonality"], "涉外收付顺差季节性,并入选择器"),
    "3.货物贸易#07": ("merged_into", ["trade_goods_seasonality"], "即期结售汇季节性,并入选择器"),
    "3.货物贸易#08": ("merged_into", ["trade_goods_seasonality"], "即远期结售汇季节性,并入选择器"),
    "3.货物贸易#09": ("retained", ["trade_goods_ttm_panel"], "出口增速3MMA与USDCNY双轴,次保留"),
    "3.货物贸易#10": ("deleted_with_reason", [], "无标题横向数据序列,指标和横轴定义不清"),
    # ── 3.贸易商 (10) ──
    "3.贸易商#01": ("retained", ["trade_merchant_settlement_ratio"], "结汇/出口结汇率双线,主保留"),
    "3.贸易商#02": ("retained", ["trade_merchant_willingness_pmi"], "意愿双线+PMI右轴,主保留"),
    "3.贸易商#03": ("deleted_with_reason", [], "无标题无系列名双线,缺可审计定义"),
    "3.贸易商#04": ("merged_into", ["trade_merchant_settlement_ratio"], "单独结汇/收入,并入结汇率图"),
    "3.贸易商#05": ("merged_into", ["trade_merchant_settlement_ratio"], "单独购汇/支出,并入结汇率图"),
    "3.贸易商#06": ("merged_into", ["trade_merchant_zscore"], "收汇结汇率Z-score,并入双Z图"),
    "3.贸易商#07": ("merged_into", ["trade_merchant_zscore"], "付汇购汇率Z-score,并入双Z图"),
    "3.贸易商#08": ("deleted_with_reason", [], "与#02主题重复,保留指标供tooltip"),
    "3.贸易商#09": ("retained", ["trade_merchant_settlement_ratio"], "意愿双线+利差右轴,次保留"),
    "3.贸易商#10": ("deleted_with_reason", [], "无标题错位双线,横轴值区间不一致"),
    # ── 3.FDI (9) ──
    "3.FDI#01": ("retained", ["fdi_seasonality"], "历史区间band+均值+当年,主保留"),
    "3.FDI#02": ("retained", ["fdi_flow"], "FDI/ODI分组柱+净流入线,主保留"),
    "3.FDI#03": ("retained", ["fdi_fx_settlement"], "结汇/购汇柱+差额3MMA线,主保留"),
    "3.FDI#04": ("merged_into", ["fdi_flow"], "FDI流入流出差额,并入统一Flow图"),
    "3.FDI#05": ("merged_into", ["fdi_flow"], "FDI流入流出差额,并入统一Flow图"),
    "3.FDI#06": ("merged_into", ["fdi_flow"], "FDI流入流出差额,并入统一Flow图"),
    "3.FDI#07": ("merged_into", ["fdi_flow"], "流入股权/债权结构,并入FDI构成"),
    "3.FDI#08": ("merged_into", ["fdi_flow"], "流出股权/债权结构,并入FDI构成"),
    "3.FDI#09": ("merged_into", ["fdi_flow"], "流入股权/债权年度,并入FDI构成"),
    # ── 3.证券EQ (7) ──
    "3.证券EQ#01": ("retained", ["sec_eq_north_south"], "北上/南下柱+合计线,主保留"),
    "3.证券EQ#02": ("merged_into", ["sec_eq_flow_vs_fx_scatter"], "净Flow与CNYX,并入统一散点"),
    "3.证券EQ#03": ("merged_into", ["sec_eq_flow_vs_fx_scatter"], "净Flow与USDCNY,并入统一散点"),
    "3.证券EQ#04": ("retained", ["sec_eq_vs_csi300"], "北上与沪深300双轴,主保留"),
    "3.证券EQ#05": ("merged_into", ["sec_eq_flow_vs_fx_scatter"], "2018以来散点,并入统一散点"),
    "3.证券EQ#06": ("merged_into", ["sec_eq_flow_vs_fx_scatter"], "过去一年半散点,并入统一散点"),
    "3.证券EQ#07": ("retained", ["sec_eq_north_south"], "港股通/陆股通累计净额,次保留"),
    # ── 3.证券FI (2) ──
    "3.证券FI#01": ("retained", ["sec_fi_bond_flows"], "资产类别堆叠柱+总流入线,主保留"),
    "3.证券FI#02": ("retained", ["sec_fi_ratebond_vs_spread_scatter"], "利率债流入与中美利差散点,次保留"),
}


def main():
    # chart_inventory.json moved to 相关开发文档/.inspection/ during folder reorg
    inv_path = PROJECT_ROOT.parent / "相关开发文档" / ".inspection" / "chart_inventory.json"
    inv = json.load(open(inv_path))
    inv_ids = {c["chart_id"] for c in inv}
    disp_ids = set(DISPOSITIONS.keys())

    # Validate
    assert len(inv) == 66, f"inventory has {len(inv)}, expected 66"
    assert inv_ids == disp_ids, f"mismatch: in inv not disp: {inv_ids - disp_ids}; in disp not inv: {disp_ids - inv_ids}"

    # Load catalog target chart_ids
    cat = json.load(open(PROJECT_ROOT / "config" / "chart_catalog.json"))
    cat_ids = set()
    for mod, md in cat["modules"].items():
        for ch in md["charts"]:
            cat_ids.add(ch["chart_id"])

    records = []
    for cid, (status, targets, reason) in sorted(DISPOSITIONS.items()):
        # Validate targets exist for retained/merged/rebuilt
        if status in ("retained", "merged_into", "rebuilt_as"):
            for t in targets:
                assert t in cat_ids, f"{cid} target {t} not in chart_catalog"
        elif status == "deleted_with_reason":
            assert reason, f"{cid} deleted without reason"
        records.append({
            "excel_chart_id": cid,
            "status": status,
            "target_chart_ids": targets,
            "reason": reason,
        })

    out = {
        "_meta": {
            "total_original_charts": 66,
            "generated": "2026-06-23",
            "source": "CHART_MIGRATION_PLAN.md + chart_inventory.json",
        },
        "dispositions": records,
    }
    out_path = PROJECT_ROOT / "config" / "excel_chart_disposition.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    # Summary
    from collections import Counter
    sc = Counter(r["status"] for r in records)
    print(f"✅ Disposition table: 66/66 charts")
    for s, c in sc.most_common():
        print(f"  {s}: {c}")
    print(f"Saved: {out_path}")


if __name__ == "__main__":
    main()
