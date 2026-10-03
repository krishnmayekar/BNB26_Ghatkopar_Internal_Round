from pathlib import Path
import base64
import hashlib
import json
import re

import pandas as pd
import streamlit as st
from PIL import Image, ExifTags
from groq import Groq

st.set_page_config(
    page_title="TrustLayer — Digital Authenticity",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

GROQ_API_KEY = ""
if ENV_FILE.exists():
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("GROQ_API_KEY="):
            GROQ_API_KEY = line.split("=", 1)[1].strip()
            break

MODEL_NAME = "qwen/qwen3.8-27b"

VALID_CLASSES = ["AUTHENTIC", "MANIPULATED", "COORDINATED_SYNTHETIC"]

SUSPICIOUS_TERMS = [
    "urgent", "breaking", "shocking", "secret", "forward",
    "100% true", "share immediately", "government confirmed",
    "must share", "viral", "exclusive", "confirmed", "real footage"
]

if not GROQ_API_KEY:
    st.error("Groq API key not found. Check your .env file.")
    st.stop()

client = Groq(api_key=GROQ_API_KEY)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');
:root {
    --ink:#e9edf5; --muted:#8791a5; --line:#242b38;
    --accent:#8cff66; --accent2:#5ce1e6;
}
html,body,[class*="css"] {font-family:'Manrope',sans-serif;}
.stApp {
    background:
      radial-gradient(circle at 12% 8%,rgba(140,255,102,.055),transparent 25%),
      radial-gradient(circle at 88% 20%,rgba(92,225,230,.045),transparent 25%),
      #090c11;
    color:var(--ink);
}
.block-container {max-width:1450px;padding-top:1.7rem;padding-bottom:4rem;}
header[data-testid="stHeader"]{background:transparent;}
.hero{display:flex;justify-content:space-between;align-items:flex-end;padding:6px 0 26px;border-bottom:1px solid var(--line);margin-bottom:22px;}
.brand-row{display:flex;align-items:center;gap:12px;}
.brand-mark{width:38px;height:38px;border:1px solid rgba(140,255,102,.55);border-radius:10px;display:grid;place-items:center;color:var(--accent);font-size:20px;box-shadow:0 0 24px rgba(140,255,102,.08);}
.brand{font-size:28px;font-weight:800;letter-spacing:-1.2px;}
.kicker,.tech{color:var(--muted);font-family:'DM Mono',monospace;font-size:10px;letter-spacing:1.6px;text-transform:uppercase;}
.live{font-family:'DM Mono',monospace;font-size:11px;color:var(--accent);border:1px solid rgba(140,255,102,.22);padding:7px 10px;border-radius:999px;background:rgba(140,255,102,.04);}
.live-dot{display:inline-block;width:6px;height:6px;background:var(--accent);border-radius:50%;margin-right:6px;box-shadow:0 0 9px var(--accent);}
.section-label{color:var(--muted);font-family:'DM Mono',monospace;font-size:10px;letter-spacing:1.6px;text-transform:uppercase;margin:10px 0;}
.card{background:linear-gradient(145deg,rgba(19,24,33,.96),rgba(12,16,22,.96));border:1px solid var(--line);border-radius:16px;padding:18px;}
.verdict{border-radius:18px;padding:23px 24px;border:1px solid;margin-bottom:14px;}
.verdict-authentic{border-color:rgba(140,255,102,.35);background:linear-gradient(120deg,rgba(140,255,102,.10),rgba(140,255,102,.025));}
.verdict-manipulated{border-color:rgba(255,100,124,.38);background:linear-gradient(120deg,rgba(255,100,124,.10),rgba(255,100,124,.025));}
.verdict-coordinated{border-color:rgba(255,200,87,.38);background:linear-gradient(120deg,rgba(255,200,87,.10),rgba(255,200,87,.025));}
.verdict-uncertain{border-color:rgba(150,160,180,.35);background:linear-gradient(120deg,rgba(150,160,180,.09),rgba(150,160,180,.025));}
.verdict-top{display:flex;justify-content:space-between;align-items:center;}
.verdict-name{font-size:29px;font-weight:800;letter-spacing:-1px;}
.verdict-tag{font-family:'DM Mono',monospace;font-size:10px;letter-spacing:1px;color:var(--muted);}
.meter{height:7px;background:#252b36;border-radius:99px;overflow:hidden;margin-top:12px;}
.meter-fill{height:100%;border-radius:99px;background:var(--accent);}
.metric-card{background:#10141c;border:1px solid var(--line);border-radius:14px;padding:14px 15px;min-height:82px;}
.metric-title{color:var(--muted);font-family:'DM Mono',monospace;font-size:9px;letter-spacing:1.2px;text-transform:uppercase;}
.metric-value{font-size:18px;font-weight:700;margin-top:8px;}
.evidence-card{background:#0f131a;border:1px solid var(--line);border-radius:15px;padding:17px;min-height:170px;}
.evidence-head{display:flex;gap:9px;align-items:center;margin-bottom:12px;}
.evidence-icon{width:29px;height:29px;display:grid;place-items:center;border-radius:8px;background:#1a202b;border:1px solid #2b3442;}
.evidence-title{font-weight:700;font-size:14px;}
.evidence-sub{color:var(--muted);font-size:10px;font-family:'DM Mono',monospace;}
.bullet{padding:8px 0;border-top:1px solid rgba(255,255,255,.055);color:#c8cfdb;font-size:13px;line-height:1.55;}
.bullet:first-child{border-top:0;}
.bullet::before{content:"→";color:var(--accent);font-family:'DM Mono',monospace;margin-right:8px;}
.chain{position:relative;padding-left:23px;}
.chain:before{content:"";position:absolute;left:5px;top:7px;bottom:7px;width:1px;background:#303846;}
.chain-item{position:relative;padding:0 0 16px 13px;color:#c9d0dc;font-size:13px;line-height:1.55;}
.chain-item:before{content:"";position:absolute;left:-21px;top:5px;width:8px;height:8px;border-radius:50%;background:#121720;border:1px solid var(--accent);}
.next-step{background:rgba(92,225,230,.045);border:1px solid rgba(92,225,230,.18);border-radius:15px;padding:17px;}
.next-step-title{color:var(--accent2);font-weight:700;margin-bottom:8px;}
.stButton>button{border-radius:11px!important;border:1px solid #303948!important;background:#151a23!important;color:#e9edf5!important;font-weight:700!important;min-height:45px!important;}
.stButton>button:hover{border-color:rgba(140,255,102,.5)!important;color:var(--accent)!important;}
div[data-testid="stFileUploader"]{background:#0f131a;border:1px solid var(--line);border-radius:14px;padding:7px;}
.stTextArea textarea,.stTextInput input{background:#0f131a!important;border:1px solid var(--line)!important;border-radius:12px!important;color:#e9edf5!important;}
.stTabs [data-baseweb="tab-list"]{gap:8px;border-bottom:1px solid var(--line);}
.stTabs [data-baseweb="tab"]{background:transparent;border-radius:9px 9px 0 0;padding:11px 16px;}
div[data-testid="stMetric"]{background:#10141c;border:1px solid var(--line);border-radius:13px;padding:11px;}
hr{border-color:var(--line)!important;}
footer{visibility:hidden;}
</style>
""", unsafe_allow_html=True)


def get_sha256(uploaded_file):
    return hashlib.sha256(uploaded_file.getvalue()).hexdigest()


def image_forensics(uploaded_file):
    uploaded_file.seek(0)
    img = Image.open(uploaded_file)
    exif_data = {}
    try:
        for key, value in img.getexif().items():
            exif_data[str(ExifTags.TAGS.get(key, key))] = str(value)
    except Exception:
        pass
    width, height = img.size
    megapixels = width * height / 1_000_000
    resolution = "LOW" if width < 500 or height < 500 else ("MODERATE" if width < 1000 or height < 1000 else "NORMAL")
    return {
        "dimensions": f"{width} × {height}",
        "format": img.format or "Unknown",
        "mode": img.mode,
        "megapixels": round(megapixels, 2),
        "exif_count": len(exif_data),
        "exif": exif_data,
        "resolution_signal": resolution,
        "sha256": get_sha256(uploaded_file),
    }


def analyze_text(text):
    text = text.strip()
    if not text:
        return {"text_present": False, "suspicious_terms": [], "observations": ["No associated text was supplied."]}
    found = [x for x in SUSPICIOUS_TERMS if x.lower() in text.lower()]
    observations = [f"Text contains {len(text)} characters."]
    observations.append(
        "Attention-seeking / forwarding patterns detected: " + ", ".join(found)
        if found else "No predefined high-pressure wording pattern detected."
    )
    return {"text_present": True, "suspicious_terms": found, "observations": observations}


def extract_json(text):
    try:
        return json.loads(text.strip())
    except Exception:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
    return None


def analyze_with_ai(uploaded_file, associated_text, forensic_data, text_data):
    uploaded_file.seek(0)
    encoded = base64.b64encode(uploaded_file.getvalue()).decode("utf-8")

    prompt = f"""
You are TrustLayer's digital authenticity reasoning engine.

Analyze BOTH the supplied image and associated text.

STRICT RULES:
- Never invent visual evidence.
- Every manipulation indicator must correspond to something actually visible.
- Do NOT call an image a collage/composite without clearly visible separate image regions.
- Do NOT infer manipulation because of busy scenes, many people/vehicles, overlap, cropping, or unusual framing.
- Absence of manipulation evidence is NOT proof of authenticity.
- Metadata absence is NOT proof of manipulation.
- Metadata presence is NOT proof of authenticity.
- Resolution alone is NOT proof of manipulation.
- Distinguish direct observation from inference.
- Inspect lighting, shadows, reflections, geometry, object boundaries, duplicates,
  anatomy, text rendering, perspective, editing seams, compression artifacts
  and impossible structures.
- Suspicious language alone must NEVER justify COORDINATED_SYNTHETIC.
- Do not claim external verification unless evidence is supplied.
- Do not assert exact date, location, identity or source without sufficient evidence.
- If evidence is insufficient or conflicting, use UNCERTAIN.

VERDICTS:
AUTHENTIC = evidence is more consistent with an ordinary original image.
MANIPULATED = concrete visible evidence indicates the image itself was altered.
COORDINATED_SYNTHETIC = image + text appear deliberately combined/constructed
to create a misleading synthetic narrative, supported by cross-modal evidence.
UNCERTAIN = insufficient or conflicting evidence.

CONFIDENCE:
LOW, MEDIUM, or HIGH only.

CROSS-MODAL CONSISTENCY:
CONSISTENT, PARTIALLY_CONSISTENT, INCONSISTENT, or UNKNOWN only.

LOCAL IMAGE FORENSICS:
{json.dumps(forensic_data, indent=2)}

LOCAL TEXT ANALYSIS:
{json.dumps(text_data, indent=2)}

ASSOCIATED TEXT:
{associated_text if associated_text.strip() else "[NO TEXT SUPPLIED]"}

Return ONLY valid JSON:

{{
  "verdict": "AUTHENTIC | MANIPULATED | COORDINATED_SYNTHETIC | UNCERTAIN",
  "confidence": "LOW | MEDIUM | HIGH",
  "image_observations": ["short directly observable facts"],
  "manipulation_indicators": ["concrete visible indicators only"],
  "text_observations": ["short observations"],
  "cross_modal_consistency": "CONSISTENT | PARTIALLY_CONSISTENT | INCONSISTENT | UNKNOWN",
  "cross_modal_reasoning": ["short reasoning points"],
  "evidence_chain": ["step 1", "step 2", "step 3"],
  "uncertainty": ["limits of what can be concluded"],
  "recommended_verification": ["practical next steps"]
}}
"""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        temperature=0.1,
        max_tokens=1800,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{encoded}"
                        }
                    }
                ]
            }
        ]
    )

    result = extract_json(response.choices[0].message.content)

    if result:
        if result.get("verdict") not in VALID_CLASSES + ["UNCERTAIN"]:
            result["verdict"] = "UNCERTAIN"

        if result.get("confidence") not in ["LOW", "MEDIUM", "HIGH"]:
            result["confidence"] = "LOW"

        if result.get("cross_modal_consistency") not in [
            "CONSISTENT",
            "PARTIALLY_CONSISTENT",
            "INCONSISTENT",
            "UNKNOWN"
        ]:
            result["cross_modal_consistency"] = "UNKNOWN"

        return result

    return {
        "verdict": "UNCERTAIN",
        "confidence": "LOW",
        "image_observations": [],
        "manipulation_indicators": [],
        "text_observations": [],
        "cross_modal_consistency": "UNKNOWN",
        "cross_modal_reasoning": [],
        "evidence_chain": [
            "The model response could not be parsed reliably."
        ],
        "uncertainty": [
            "Structured analysis was unavailable."
        ],
        "recommended_verification": [
            "Repeat the analysis."
        ]
    }
def evidence_card(icon, title, subtitle, items):
    html = f"""
    <div class="evidence-card">
      <div class="evidence-head">
        <div class="evidence-icon">{icon}</div>
        <div><div class="evidence-title">{title}</div>
        <div class="evidence-sub">{subtitle}</div></div>
      </div>
    """
    if not items:
        items = ["Nothing notable detected."]
    for item in items:
        html += f'<div class="bullet">{str(item)}</div>'
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)


def render_verdict(result):
    verdict = result.get("verdict", "UNCERTAIN")
    confidence = result.get("confidence", "LOW")
    classes = {
        "AUTHENTIC": ("verdict-authentic", "✓", "LOW RISK"),
        "MANIPULATED": ("verdict-manipulated", "!", "MANIPULATION SIGNAL"),
        "COORDINATED_SYNTHETIC": ("verdict-coordinated", "◆", "CROSS-MODAL RISK"),
        "UNCERTAIN": ("verdict-uncertain", "?", "INSUFFICIENT EVIDENCE")
    }
    css, icon, tag = classes.get(verdict, classes["UNCERTAIN"])
    meter = {"LOW": 28, "MEDIUM": 62, "HIGH": 91}.get(confidence, 28)
    text = {"LOW": "Limited evidence", "MEDIUM": "Moderate evidence", "HIGH": "Strong evidence"}.get(confidence, "Limited evidence")

    st.markdown(f"""
    <div class="verdict {css}">
      <div class="verdict-top">
        <div>
          <div class="verdict-tag">{tag}</div>
          <div class="verdict-name">{icon} {verdict.replace("_"," ")}</div>
        </div>
        <div style="text-align:right">
          <div class="verdict-tag">CONFIDENCE</div>
          <div style="font-size:19px;font-weight:800">{confidence}</div>
        </div>
      </div>
      <div class="meter"><div class="meter-fill" style="width:{meter}%"></div></div>
      <div class="tech" style="margin-top:8px">{text}</div>
    </div>
    """, unsafe_allow_html=True)


def evaluate_files(files, label, texts):
    results = []
    for uploaded_file in files:
        try:
            forensic = image_forensics(uploaded_file)
            text = texts.get(uploaded_file.name, "")
            text_data = analyze_text(text)
            result = analyze_with_ai(uploaded_file, text, forensic, text_data)
            prediction = result.get("verdict", "UNCERTAIN")
            results.append({
                "Image": uploaded_file.name,
                "Actual": label,
                "Predicted": prediction,
                "Confidence": result.get("confidence", "LOW"),
                "Correct": prediction == label
            })
        except Exception:
            results.append({
                "Image": uploaded_file.name,
                "Actual": label,
                "Predicted": "ERROR",
                "Confidence": "LOW",
                "Correct": False
            })
    return results


# HEADER
st.markdown("""
<div class="hero">
  <div>
    <div class="brand-row">
      <div class="brand-mark">◈</div>
      <div>
        <div class="brand">TRUSTLAYER</div>
        <div class="kicker">MULTIMODAL AUTHENTICITY ENGINE / v1.0</div>
      </div>
    </div>
  </div>
  <div class="live"><span class="live-dot"></span>ANALYSIS ENGINE ONLINE</div>
</div>
""", unsafe_allow_html=True)

tabs = st.tabs(["◈  INVESTIGATE", "▦  EVALUATE"])

with tabs[0]:
    st.markdown('<div class="section-label">01 / Digital evidence intake</div>', unsafe_allow_html=True)
    left, right = st.columns([1.05, .95], gap="large")

    with left:
        uploaded_file = st.file_uploader(
            "Drop an image into the investigation",
            type=["jpg","jpeg","png","webp"],
            key="main_upload"
        )
        if uploaded_file:
            st.image(uploaded_file, use_container_width=True)
            st.markdown(f'<div class="tech">EVIDENCE FILE · {uploaded_file.name}</div>', unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="card" style="height:420px;display:grid;place-items:center;text-align:center">
              <div><div style="font-size:42px;color:#586274">◈</div>
              <div style="font-size:18px;font-weight:700;margin-top:10px">Awaiting visual evidence</div>
              <div class="tech" style="margin-top:8px">JPG · PNG · WEBP</div></div>
            </div>
            """, unsafe_allow_html=True)

    with right:
        st.markdown('<div class="section-label">02 / Context signal</div>', unsafe_allow_html=True)
        associated_text = st.text_area(
            "Associated message, caption or claim",
            placeholder="Paste the text that came with this image…",
            height=150,
            label_visibility="collapsed"
        )
        st.markdown('<div class="section-label">03 / Analysis scope</div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="card">
          <div class="tech">TRUSTLAYER WILL CROSS-CHECK</div>
          <div style="margin-top:12px;line-height:2;color:#c9d0dc;font-size:13px">
            ◈ Visual manipulation signals<br>
            ◈ Image metadata & fingerprint<br>
            ◈ Linguistic pressure signals<br>
            ◈ Image ↔ text consistency<br>
            ◈ Evidence confidence & uncertainty
          </div>
        </div>
        """, unsafe_allow_html=True)
        st.write("")
        analyze_button = st.button("RUN TRUST ANALYSIS  →", type="primary", use_container_width=True)

    if analyze_button:
        if not uploaded_file:
            st.warning("Upload an image first.")
        else:
            forensic = image_forensics(uploaded_file)
            text_data = analyze_text(associated_text)
            with st.spinner("Cross-examining evidence…"):
                result = analyze_with_ai(uploaded_file, associated_text, forensic, text_data)
            st.session_state["result"] = result
            st.session_state["forensic"] = forensic
            st.session_state["text_data"] = text_data

    if "result" in st.session_state:
        result = st.session_state["result"]
        forensic = st.session_state["forensic"]
        text_data = st.session_state["text_data"]

        st.divider()
        st.markdown('<div class="section-label">04 / Investigation finding</div>', unsafe_allow_html=True)
        render_verdict(result)

        c1,c2,c3,c4 = st.columns(4)
        metrics = [
            ("CROSS-MODAL", result.get("cross_modal_consistency","UNKNOWN")),
            ("IMAGE SIZE", forensic.get("dimensions","—")),
            ("EXIF FIELDS", str(forensic.get("exif_count",0))),
            ("TEXT SIGNALS", str(len(text_data.get("suspicious_terms",[]))))
        ]
        for col,(title,value) in zip([c1,c2,c3,c4],metrics):
            with col:
                st.markdown(f'<div class="metric-card"><div class="metric-title">{title}</div><div class="metric-value">{value}</div></div>', unsafe_allow_html=True)

        st.write("")
        a,b,c = st.columns(3,gap="medium")
        with a:
            evidence_card("◉","WHAT THE AI SEES","DIRECT VISUAL OBSERVATIONS",result.get("image_observations",[]))
        with b:
            evidence_card("⌁","CROSS-MODAL CHECK","IMAGE + TEXT RELATIONSHIP",result.get("cross_modal_reasoning",[]))
        with c:
            evidence_card("△","FORENSIC SIGNALS","CONCRETE WARNING INDICATORS",result.get("manipulation_indicators",[]))

        st.write("")
        left2,right2 = st.columns([1.15,.85],gap="large")
        with left2:
            st.markdown('<div class="section-label">05 / Why TrustLayer reached this finding</div>', unsafe_allow_html=True)
            chain = result.get("evidence_chain",[])
            chain_html = '<div class="card"><div class="chain">'
            for i,item in enumerate(chain,1):
                chain_html += f'<div class="chain-item"><span class="tech">STEP {i:02d}</span><br>{str(item)}</div>'
            if not chain:
                chain_html += '<div class="chain-item">No evidence chain returned.</div>'
            chain_html += "</div></div>"
            st.markdown(chain_html,unsafe_allow_html=True)

        with right2:
            st.markdown('<div class="section-label">06 / Decision limits</div>', unsafe_allow_html=True)
            uncertainties = result.get("uncertainty",[])
            unc_html = '<div class="card">'
            if uncertainties:
                for item in uncertainties:
                    unc_html += f'<div class="bullet">{str(item)}</div>'
            else:
                unc_html += '<div class="bullet">No additional uncertainty reported.</div>'
            unc_html += "</div>"
            st.markdown(unc_html,unsafe_allow_html=True)
            st.write("")
            st.markdown('<div class="next-step"><div class="next-step-title">NEXT VERIFICATION</div>',unsafe_allow_html=True)
            for item in result.get("recommended_verification",[]):
                st.markdown(f'<div class="bullet">{str(item)}</div>',unsafe_allow_html=True)
            st.markdown("</div>",unsafe_allow_html=True)

        with st.expander("⌘ TECHNICAL FORENSICS"):
            x,y = st.columns(2)
            with x:
                st.write("**Format:**",forensic.get("format"))
                st.write("**Color mode:**",forensic.get("mode"))
                st.write("**Megapixels:**",forensic.get("megapixels"))
                st.write("**Resolution signal:**",forensic.get("resolution_signal"))
            with y:
                st.write("**SHA-256 fingerprint**")
                st.code(forensic.get("sha256",""))
            st.write("**EXIF metadata**")
            if forensic.get("exif"):
                st.json(forensic["exif"])
            else:
                st.caption("No EXIF metadata found.")

with tabs[1]:
    st.markdown('<div class="section-label">Evaluation laboratory / Ground-truth testing</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="card">
      <div style="font-size:16px;font-weight:700">Test the engine against known examples.</div>
      <div style="color:#8b95a7;font-size:12px;margin-top:6px">
      No filename rules. No .txt files. Upload images directly into their
      ground-truth category. Optional text can be supplied per image.
      </div>
    </div>
    """,unsafe_allow_html=True)
    st.write("")
    e1,e2,e3 = st.columns(3,gap="medium")
    with e1:
        st.markdown('<div class="section-label">AUTHENTIC</div>',unsafe_allow_html=True)
        authentic = st.file_uploader("Known authentic examples",type=["jpg","jpeg","png","webp"],accept_multiple_files=True,key="eval_auth")
    with e2:
        st.markdown('<div class="section-label">MANIPULATED</div>',unsafe_allow_html=True)
        manipulated = st.file_uploader("Known manipulated examples",type=["jpg","jpeg","png","webp"],accept_multiple_files=True,key="eval_man")
    with e3:
        st.markdown('<div class="section-label">COORDINATED</div>',unsafe_allow_html=True)
        coordinated = st.file_uploader("Known coordinated examples",type=["jpg","jpeg","png","webp"],accept_multiple_files=True,key="eval_coord")

    all_eval = authentic + manipulated + coordinated
    eval_texts = {}
    if all_eval:
        st.markdown('<div class="section-label">Optional associated text</div>',unsafe_allow_html=True)
        cols = st.columns(2)
        for i,file in enumerate(all_eval):
            with cols[i%2]:
                eval_texts[file.name] = st.text_input(file.name,key=f"eval_text_{file.name}")
        st.write("")

    if st.button("RUN EVALUATION  →",type="primary",use_container_width=True):
        if not all_eval:
            st.warning("Upload at least one labeled image.")
        else:
            progress = st.progress(0)
            results = []
            groups = [(authentic,"AUTHENTIC"),(manipulated,"MANIPULATED"),(coordinated,"COORDINATED_SYNTHETIC")]
            total = len(all_eval)
            done = 0
            for files,label in groups:
                if files:
                    results.extend(evaluate_files(files,label,eval_texts))
                    done += len(files)
                    progress.progress(done/total)
            st.session_state["eval_results"] = results

    if "eval_results" in st.session_state:
        results = st.session_state["eval_results"]
        total = len(results)
        correct = sum(x["Correct"] for x in results)
        accuracy = correct/total*100 if total else 0
        uncertain = sum(x["Predicted"]=="UNCERTAIN" for x in results)

        st.divider()
        r1,r2,r3,r4 = st.columns(4)
        for col,title,value in [(r1,"SAMPLES",total),(r2,"CORRECT",correct),(r3,"ACCURACY",f"{accuracy:.1f}%"),(r4,"UNCERTAIN",uncertain)]:
            with col:
                st.markdown(f'<div class="metric-card"><div class="metric-title">{title}</div><div class="metric-value">{value}</div></div>',unsafe_allow_html=True)

        st.write("")
        st.markdown('<div class="section-label">Class performance</div>',unsafe_allow_html=True)
        rows=[]
        for label in VALID_CLASSES:
            subset=[x for x in results if x["Actual"]==label]
            cc=sum(x["Correct"] for x in subset)
            rows.append({"Class":label.replace("_"," "),"Samples":len(subset),"Correct":cc,"Accuracy":f"{cc/len(subset)*100:.1f}%" if subset else "—"})
        st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)

        st.markdown('<div class="section-label">Confusion matrix</div>',unsafe_allow_html=True)
        labels=VALID_CLASSES+["UNCERTAIN"]
        matrix=pd.DataFrame(0,index=VALID_CLASSES,columns=labels)
        for row in results:
            if row["Actual"] in matrix.index and row["Predicted"] in matrix.columns:
                matrix.loc[row["Actual"],row["Predicted"]]+=1
        st.dataframe(matrix,use_container_width=True)

        st.markdown('<div class="section-label">Sample audit trail</div>',unsafe_allow_html=True)
        st.dataframe(pd.DataFrame(results),use_container_width=True,hide_index=True)

st.markdown("""
<div style="text-align:center;margin-top:45px;color:#566071;font-family:'DM Mono',monospace;font-size:9px;letter-spacing:1.5px">
TRUSTLAYER / DIGITAL AUTHENTICITY & TRUST / MULTIMODAL AI PROTOTYPE
</div>
""",unsafe_allow_html=True)
