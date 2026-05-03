"""
SmartSplit Bill AI — Streamlit UI
Upload a receipt photo → extract items with Gemini → split the bill.

Implements all three prompt iterations from the PPTX:
  Prompt 01: Scaffold (upload, extract, editable table, split)
  Prompt 02: Fix (separate tax/service, reset, side-by-side image)
  Prompt 03: Polish (checkbox grid, live totals, rounding badge, CSV export, styling)
"""

import io
import csv

import pandas as pd
import streamlit as st

from extractor import extract_receipt, validate_totals
from extractor_ocr import extract_receipt_ocr
from splitter import compute_split, format_currency

st.set_page_config(
    page_title="SmartSplit Bill AI",
    page_icon="🧾",
    layout="wide",
    initial_sidebar_state="collapsed",
)

HIDE_STREAMLIT_STYLE = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* Dark gradient background */
.stApp {
    background: linear-gradient(to bottom right, #0f172a, #1e293b);
    color: white;
}

/* Gradient text for header */
.header-accent {
    background: -webkit-linear-gradient(45deg, #3b82f6, #8b5cf6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 2.5rem;
    font-weight: bold;
    margin-bottom: 0px;
}

/* Step number pill */
.step-number {
    display: inline-block;
    width: 28px;
    height: 28px;
    background: #3b82f6;
    color: white;
    border-radius: 50%;
    text-align: center;
    line-height: 28px;
    font-weight: bold;
    margin-right: 10px;
}

/* Badges */
.success-badge {
    background-color: rgba(34, 197, 94, 0.2);
    color: #4ade80;
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 0.9rem;
    border: 1px solid rgba(34, 197, 94, 0.5);
}

.warning-badge {
    background-color: rgba(234, 179, 8, 0.2);
    color: #facc15;
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 0.9rem;
    border: 1px solid rgba(234, 179, 8, 0.5);
}

.error-badge {
    background-color: rgba(239, 68, 68, 0.2);
    color: #f87171;
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 0.9rem;
    border: 1px solid rgba(239, 68, 68, 0.5);
}
</style>
"""

st.markdown(HIDE_STREAMLIT_STYLE, unsafe_allow_html=True)

def _init_state():
    defaults = {
        "bill_data": None,
        "raw_response": None,
        "extraction_error": None,
        "extraction_time": None,
        "uploaded_image": None,
        "participants": [],
        "assignments": {},
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


_init_state()

col_title, col_reset = st.columns([8, 2])
with col_title:
    st.markdown('<p class="header-accent">🧾 SmartSplit Bill AI</p>', unsafe_allow_html=True)
    st.caption("Upload a receipt · Extract items with Gemini · Split the bill fairly")

with col_reset:
    st.write("")
    st.write("")
    if st.button("🔄 Reset", key="reset_btn", use_container_width=True):
        for key in ["bill_data", "raw_response", "extraction_error", "extraction_time",
                     "uploaded_image", "participants", "assignments"]:
            st.session_state[key] = None if key != "participants" and key != "assignments" else ([] if key == "participants" else {})
        st.rerun()

st.divider()

st.markdown('<div class="step-number">1</div> <b>Upload Receipt Image</b>', unsafe_allow_html=True)

uploaded_file = st.file_uploader(
    "Drag and drop or click to upload (JPG / PNG)",
    type=["jpg", "jpeg", "png"],
    key="file_uploader",
    label_visibility="collapsed",
)

if uploaded_file is not None:
    st.session_state["uploaded_image"] = uploaded_file.getvalue()
    mime = "image/jpeg" if uploaded_file.type in ("image/jpeg", "image/jpg") else "image/png"
    st.image(uploaded_file, caption="Uploaded Receipt", width=350)

    st.markdown("---")
    st.markdown('<div class="step-number">2</div> <b>Extract Items</b>', unsafe_allow_html=True)

    method = st.radio(
        "Extraction method",
        ["🤖 Gemini AI (API)", "📷 Offline OCR (EasyOCR)"],
        horizontal=True,
        help="Gemini AI: accurate, needs internet + API key. Offline OCR: no API key, works locally, less accurate.",
    )

    use_gemini = method.startswith("🤖")
    btn_label = "⚡ Extract with Gemini" if use_gemini else "🔍 Extract with OCR (Offline)"
    spinner_text = "🔍 Analyzing receipt with Gemini 2.5 Flash..." if use_gemini else "🔍 Running EasyOCR (first run downloads ~200 MB)..."

    if st.button(btn_label, key="extract_btn", type="primary", use_container_width=True):
        with st.spinner(spinner_text):
            if use_gemini:
                result = extract_receipt(uploaded_file.getvalue(), mime)
            else:
                result = extract_receipt_ocr(uploaded_file.getvalue(), mime)
            st.session_state["bill_data"] = result["data"]
            st.session_state["raw_response"] = result["raw"]
            st.session_state["extraction_error"] = result["error"]
            st.session_state["extraction_time"] = result["time_s"]
            st.session_state["assignments"] = {}
            st.rerun()

    if st.session_state["extraction_error"] and st.session_state["bill_data"] is None:
        st.error(f"Extraction failed: {st.session_state['extraction_error']}")
        with st.expander("Raw model response"):
            st.code(st.session_state["raw_response"], language="json")

    elif st.session_state["bill_data"] is not None:
        bill = st.session_state["bill_data"]

        if st.session_state["extraction_time"]:
            st.success(f"✅ Extracted in {st.session_state['extraction_time']:.1f}s")

        validation = validate_totals(bill)
        if not validation["valid"]:
            st.warning(
                f"⚠️ Totals mismatch: items ({validation['items_sum']:,.0f}) + "
                f"extras ({validation['extras_sum']:,.0f}) = {validation['items_sum'] + validation['extras_sum']:,.0f}, "
                f"but receipt says {validation['expected']:,.0f}. Diff: {validation['diff_pct']:.1%}"
            )

        col_info1, col_info2, col_info3 = st.columns(3)
        with col_info1:
            st.metric("Merchant", bill.get("merchant", "Unknown"))
        with col_info2:
            st.metric("Currency", bill.get("currency", "—"))
        with col_info3:
            st.metric("Grand Total", format_currency(bill.get("total", 0), bill.get("currency", "IDR")))

        st.markdown("---")

        col_image, col_table = st.columns([1, 2])
        with col_image:
            st.markdown("**Receipt Preview**")
            if st.session_state["uploaded_image"]:
                st.image(st.session_state["uploaded_image"], use_container_width=True)

        with col_table:
            st.markdown("**Line Items** — _fully editable_")
            items_df = pd.DataFrame(bill.get("items", []))
            if not items_df.empty:
                edited_items = st.data_editor(
                    items_df,
                    key="items_editor",
                    use_container_width=True,
                    num_rows="dynamic",
                    column_config={
                        "name": st.column_config.TextColumn("Item", width="large"),
                        "qty": st.column_config.NumberColumn("Qty", min_value=0, format="%d"),
                        "unit_price": st.column_config.NumberColumn("Unit Price", format="%.0f"),
                        "total": st.column_config.NumberColumn("Total", format="%.0f"),
                    },
                )
                bill["items"] = edited_items.to_dict("records")

        if bill.get("extras"):
            st.markdown("**Extras (Tax / Service / Discounts)**")
            extras_df = pd.DataFrame(bill["extras"])
            edited_extras = st.data_editor(
                extras_df,
                key="extras_editor",
                use_container_width=True,
                column_config={
                    "label": st.column_config.TextColumn("Label", width="medium"),
                    "amount": st.column_config.NumberColumn("Amount", format="%.0f"),
                },
            )
            bill["extras"] = edited_extras.to_dict("records")

        st.markdown("---")

        st.markdown('<div class="step-number">3</div> <b>Who is splitting?</b>', unsafe_allow_html=True)

        names_input = st.text_input(
            "Enter names separated by commas",
            value=", ".join(st.session_state["participants"]) if st.session_state["participants"] else "",
            placeholder="e.g. Andre, Budi, Cici, Dina",
            key="names_input",
        )

        if names_input:
            participants = [n.strip() for n in names_input.split(",") if n.strip()]
            st.session_state["participants"] = participants
        else:
            participants = []
            st.session_state["participants"] = []

        if participants and bill.get("items"):
            st.markdown("---")
            st.markdown(
                '<div class="step-number">4</div> <b>Assign items to people</b> '
                '<span style="color:#94a3b8; font-size:0.9rem;">— check who ate what</span>',
                unsafe_allow_html=True,
            )

            items = bill["items"]

            col_config = {
                "Item": st.column_config.TextColumn("Item", disabled=True, width="large"),
                "Total": st.column_config.NumberColumn("Total", disabled=True, format="%.0f"),
            }
            for person in participants:
                col_config[person] = st.column_config.CheckboxColumn(person, default=False)

            _cache_key = f"{bill.get('merchant','')}|{len(items)}|{'|'.join(participants)}"
            if st.session_state.get("_asgn_cache_key") != _cache_key:
                rows = [
                    {
                        "Item": item.get("name", f"Item {idx+1}"),
                        "Total": item.get("total", 0),
                        **{p: False for p in participants},
                    }
                    for idx, item in enumerate(items)
                ]
                st.session_state["_asgn_df"] = pd.DataFrame(rows)
                st.session_state["_asgn_cache_key"] = _cache_key

            edited_assignments = st.data_editor(
                st.session_state["_asgn_df"],
                key="assignment_grid",
                use_container_width=True,
                column_config=col_config,
                hide_index=True,
            )

            new_assignments = {}
            for idx in range(len(items)):
                consumers = set()
                for person in participants:
                    if edited_assignments.iloc[idx].get(person, False):
                        consumers.add(person)
                new_assignments[idx] = consumers
            st.session_state["assignments"] = new_assignments

            st.markdown("---")
            st.markdown(
                '<div class="step-number">5</div> <b>Per-person totals</b> '
                '<span style="color:#94a3b8; font-size:0.9rem;">— updates live</span>',
                unsafe_allow_html=True,
            )

            split_result = compute_split(
                items=bill["items"],
                extras=bill.get("extras", []),
                bill_total=bill.get("total", 0),
                assignments=new_assignments,
                participants=participants,
            )

            currency = bill.get("currency", "IDR")

            metric_cols = st.columns(len(participants))
            for i, person in enumerate(participants):
                info = split_result[person]
                with metric_cols[i]:
                    st.metric(
                        label=f"👤 {person}",
                        value=format_currency(info["total"], currency),
                    )
                    if info["total"] == 0:
                        st.caption(f"_{person} has no assigned items — they pay 0._")

            per_person_sum = sum(r["total"] for r in split_result.values())
            rounding_diff = abs(per_person_sum - (bill.get("total", 0) or 0))

            if rounding_diff <= 100:
                if rounding_diff > 0:
                    st.markdown(
                        f'<span class="success-badge">✓ Rounding diff: {rounding_diff:,.0f} {currency} — within tolerance</span>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        '<span class="success-badge">✓ Perfectly balanced</span>',
                        unsafe_allow_html=True,
                    )
            else:
                st.markdown(
                    f'<span class="error-badge">⚠ Split diff: {rounding_diff:,.0f} {currency} — check assignments</span>',
                    unsafe_allow_html=True,
                )

            with st.expander("📊 Detailed breakdown"):
                for person in participants:
                    info = split_result[person]
                    st.markdown(f"**{person}**")
                    if info["items_detail"]:
                        detail_df = pd.DataFrame(info["items_detail"], columns=["Item", "Share"])
                        detail_df["Share"] = detail_df["Share"].apply(lambda x: format_currency(x, currency))
                        st.dataframe(detail_df, hide_index=True, use_container_width=True)
                    st.caption(
                        f"Items subtotal: {format_currency(info['items_subtotal'], currency)} · "
                        f"Extras share: {format_currency(info['extras_share'], currency)} · "
                        f"**Total: {format_currency(info['total'], currency)}**"
                    )
                    st.divider()

            st.markdown("---")

            csv_buffer = io.StringIO()
            writer = csv.writer(csv_buffer)
            writer.writerow(["Person", "Amount", "Items"])
            for person in participants:
                info = split_result[person]
                item_names = ", ".join(name for name, _ in info["items_detail"])
                writer.writerow([person, info["total"], item_names])

            st.download_button(
                label="📥 Export Split as CSV",
                data=csv_buffer.getvalue(),
                file_name="smartsplit_result.csv",
                mime="text/csv",
                key="csv_export",
                use_container_width=True,
            )

        with st.expander("📄 Raw OCR / model text"):
            st.code(st.session_state["raw_response"] or "", language=None)

        with st.expander("🔧 Parsed JSON (structured output)"):
            st.json(bill)

elif st.session_state["bill_data"] is None:
    st.info("👆 Upload a receipt image to get started")

st.markdown("---")
st.caption("SmartSplit Bill AI · Day 56 · ML Bootcamp · Gemini 2.5 Flash or EasyOCR")
