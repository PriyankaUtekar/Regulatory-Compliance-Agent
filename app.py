"""
Gradio Front-End — GDPR + EU AI Act Compliance Co-Pilot
========================================================
A clean, demo-ready browser UI that calls the compliance pipeline
and renders the report in Markdown with visual risk indicators.

Usage:
    cd d:\\compliance_agent
    .venv\\Scripts\\python.exe app.py

Opens at http://127.0.0.1:7860 by default.
"""

import asyncio
import threading

# Load environment variables (OPENAI_API_KEY) from .env before anything else
from dotenv import load_dotenv
load_dotenv()

import gradio as gr

# Import the pipeline function from the root orchestrator
from agent import run_compliance_check


# ---------------------------------------------------------------------------
# Wrapper: bridge async run_compliance_check into Gradio's sync callback
# ---------------------------------------------------------------------------
def run_check(description: str, progress=gr.Progress()) -> str:
    """
    Synchronous wrapper around the async run_compliance_check().
    Gradio calls this when the user clicks the button.

    Returns the final compliance report as Markdown, or an error message.
    Uses a background thread + new event loop to safely call async code
    regardless of Gradio's own event loop state.
    """
    # Validate input
    if not description or not description.strip():
        return (
            "## ⚠️ Please enter a description\n\n"
            "Describe the AI system you want to evaluate. For example:\n\n"
            '*"An AI tool that screens job applicant resumes and ranks candidates"*'
        )

    progress(0, desc="🔄 Starting compliance pipeline...")

    result_holder = {}

    def _run_in_thread():
        """Run async pipeline in a clean event loop on a separate thread."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result_holder["report"] = loop.run_until_complete(
                run_compliance_check(description.strip())
            )
        except Exception as e:
            result_holder["error"] = str(e)
        finally:
            loop.close()

    thread = threading.Thread(target=_run_in_thread)
    thread.start()

    # Poll for progress updates while thread runs
    import time
    messages = [
        (0.1, "🧠 Extracting structured fields from description..."),
        (0.35, "⚖️  Evaluating GDPR checkpoints in parallel..."),
        (0.55, "🤖 Classifying EU AI Act risk tier in parallel..."),
        (0.80, "📋 Aggregating findings into final report..."),
        (0.95, "✅ Almost done — finalising report..."),
    ]
    for frac, msg in messages:
        if not thread.is_alive():
            break
        progress(frac, desc=msg)
        time.sleep(2.5)

    thread.join()
    progress(1.0, desc="✅ Complete!")

    if "error" in result_holder:
        error_msg = result_holder["error"]
        if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg or "rate_limit" in error_msg.lower():
            return (
                "## 🚫 API Quota / Rate Limit Exceeded\n\n"
                "The API quota has been exhausted. Please wait a moment and try again, "
                "or update the API key in `.env` with a higher-tier key.\n\n"
                f"*Technical detail: `{error_msg[:300]}`*"
            )
        elif "authentication" in error_msg.lower() or "api_key" in error_msg.lower() or "401" in error_msg:
            return (
                "## 🔑 Authentication Error\n\n"
                "The API key in `.env` appears to be invalid or missing.\n\n"
                "Check that `OPENAI_API_KEY` is set correctly in your `.env` file.\n\n"
                f"*Technical detail: `{error_msg[:300]}`*"
            )
        else:
            return (
                "## ❌ Error Running Pipeline\n\n"
                f"An error occurred while running the compliance check:\n\n"
                f"```\n{error_msg[:600]}\n```\n\n"
                "Check the terminal for full details."
            )

    report = result_holder.get("report", "")
    if not report:
        return (
            "## ⚠️ No Report Generated\n\n"
            "The pipeline completed but returned an empty response. "
            "This may indicate an issue with the API key or model availability. "
            "Check the terminal for error details."
        )

    return report



# ---------------------------------------------------------------------------
# Example inputs — cover all 5 test scenarios for judges / demo
# ---------------------------------------------------------------------------
EXAMPLES = [
    [
        "We are deploying an AI-powered resume screening tool for our HR department that "
        "automatically parses uploaded CVs and ranks job applicants on a scale of 1 to 100 "
        "based on skills, work experience, education, and inferred cultural fit. "
        "The system processes personal data including full names, addresses, employment history, "
        "educational qualifications, and any LinkedIn profile links candidates choose to include. "
        "Candidates who score below 60 are automatically rejected without any human review, "
        "while those above 80 are fast-tracked directly to a first-round interview. "
        "The tool will be used across all EU member state hiring operations and is expected to "
        "process approximately 50,000 applications per year. "
        "Planned release date: October 15, 2026."
    ],
    [
        "Our e-commerce platform has developed an in-house AI-powered customer support chatbot to handle "
        "common enquiries such as order tracking, return requests, product questions, and "
        "complaints — available 24/7 in place of live agents for Tier-1 support. "
        "The chatbot uses the customer's order ID and email address to look up order status "
        "but does not store any conversation logs beyond the current session, and it never "
        "requests payment details, passwords, or sensitive personal information. "
        "All unresolved issues are escalated to a human agent after two failed resolution attempts. "
        "The system will serve customers across the UK and EU, handling an estimated "
        "10,000 interactions per day. "
        "Planned release date: September 1, 2026."
    ],
    [
        "A major retail bank is deploying an AI credit-scoring model that evaluates loan "
        "applications and produces a creditworthiness score used to approve, conditionally "
        "approve, or reject personal loan requests of up to €50,000. "
        "The model ingests applicant data including income, employment status, existing debt, "
        "credit history, residential postcode, and self-declared spending habits collected "
        "from the loan application form. "
        "Decisions made by the model are fully automated for applications below €10,000 "
        "with no mandatory human review step; a loan officer only intervenes for larger amounts "
        "or when the model confidence score falls below a set threshold. "
        "The system will be used in Germany, France, and the Netherlands and is expected to "
        "process around 200,000 applications annually. "
        "Planned release date: November 20, 2026."
    ],
    [
        "Our marketing agency is building an AI image generation service that creates original "
        "promotional visuals, social media banners, and product lifestyle shots on demand "
        "for small business clients who cannot afford professional photography. "
        "Users describe the image they want in plain text and the system returns up to five "
        "generated image options; users select and download whichever they prefer. "
        "No personal data about end consumers is collected or processed — only the business "
        "client's account email and billing information are stored, solely for invoicing purposes. "
        "The generated images are used purely for advertising and contain no biometric data, "
        "political content, or representations of real identifiable individuals. "
        "Planned release date: December 5, 2026."
    ],
    [
        "We are a logistics company deploying an AI-powered safety component on our fleet of warehouse "
        "forklifts that automatically detects pedestrians and halts the machinery to prevent collisions. "
        "This system operates entirely locally on the forklift, processing real-time video feeds from "
        "onboard cameras without recording or transmitting any footage or personal data. "
        "The system is a safety component of machinery covered under EU product safety regulations, "
        "and we are using it strictly in accordance with the manufacturer's instructions. "
        "It will be deployed across our warehouse operations in Germany and Poland. "
        "Planned release date: March 1, 2027."
    ],
    [
        "We are an established medical device manufacturer developing a new MRI machine with an embedded AI component "
        "that assists radiologists in diagnosing potential tumors from scans. "
        "The system processes pseudonymised patient scan data and outputs a bounding box highlighting areas of concern. "
        "The final diagnostic decision is always made by a qualified human radiologist, and the AI acts solely as a second-reader support tool. "
        "The device will be sold to hospitals across the EU and UK, with an expected rollout in early 2027. "
        "Patient data is stored locally on the hospital's secure servers and is not transmitted back to us for training purposes. "
        "Planned release date: January 10, 2027."
    ],
]

# ---------------------------------------------------------------------------
# Custom CSS — clean, readable styling that works inside Gradio's Soft theme
# ---------------------------------------------------------------------------
CUSTOM_CSS = """
/* ---- Header ---- */
.main-title {
    text-align: center;
    font-size: 2rem !important;
    font-weight: 700 !important;
    margin-bottom: 0.25rem !important;
    background: linear-gradient(135deg, #1e40af, #7c3aed);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

/* ---- Disclaimer banner ---- */
.disclaimer-banner {
    background: #fef3c7 !important;
    border: 1px solid #f59e0b !important;
    border-radius: 8px !important;
    padding: 0.6rem 1.2rem !important;
    text-align: center !important;
    color: #92400e !important;
    font-size: 0.88rem !important;
    margin-bottom: 1rem !important;
}

/* ---- Run button ---- */
#run-btn {
    background: linear-gradient(135deg, #1e40af, #7c3aed) !important;
    color: white !important;
    font-size: 1.05rem !important;
    font-weight: 600 !important;
    border-radius: 8px !important;
    border: none !important;
    padding: 0.7rem 1.5rem !important;
    transition: opacity 0.2s ease !important;
    width: 100%;
}
#run-btn:hover { opacity: 0.88 !important; }

/* ---- Report output panel ---- */
.report-panel {
    min-height: 480px;
    background: #f8fafc !important;
    border-radius: 10px !important;
    padding: 1rem !important;
    border: 1px solid #e2e8f0 !important;
}
.report-panel p, .report-panel li, .left-panel p, .left-panel li {
    font-size: 1rem !important;
    line-height: 1.6 !important;
}

/* ---- Examples section ---- */
.examples-header, .examples-header h3, .examples-header p {
    font-size: 1rem !important;
    font-weight: 600 !important;
    color: #475569 !important;
    margin-top: 1rem !important;
    margin-bottom: 0.25rem !important;
}

/* ---- Example scenario buttons ---- */
button.secondary {
    background: #f1f5f9 !important;
    color: #1e40af !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 6px !important;
    font-size: 1rem !important;
    font-weight: 500 !important;
    text-align: left !important;
    padding: 0.45rem 0.75rem !important;
    transition: background 0.15s ease, border-color 0.15s ease !important;
    width: 100% !important;
    margin-bottom: 4px !important;
}
button.secondary:hover {
    background: #dbeafe !important;
    border-color: #93c5fd !important;
}

/* ---- Tables ---- */
.report-panel table {
    width: 100% !important;
    border-collapse: collapse !important;
    margin-top: 1rem !important;
    margin-bottom: 1rem !important;
}
.report-panel th {
    background-color: #f1f5f9 !important;
    font-weight: 600 !important;
    text-align: left !important;
    padding: 0.75rem !important;
    border: 1px solid #cbd5e1 !important;
}
.report-panel td {
    padding: 0.75rem !important;
    border: 1px solid #cbd5e1 !important;
    vertical-align: top !important;
}
.report-panel td:nth-child(2), .report-panel th:nth-child(2) {
    text-align: center !important;
    width: 120px;
}
.report-panel td:nth-child(3), .report-panel th:nth-child(3) {
    text-align: center !important;
    width: 120px;
}
"""

# ---------------------------------------------------------------------------
# Build the Gradio UI using gr.Blocks for full layout control
# ---------------------------------------------------------------------------
with gr.Blocks(
    title="GDPR + EU AI Act Compliance Co-Pilot",
) as app:

    # ---- Header ----
    gr.Markdown(
        "# 🛡️ GDPR + EU AI Act Compliance Co-Pilot",
        elem_classes=["main-title"],
    )

    gr.Markdown(
        "⚠️ **A first-pass readiness check — not legal advice.** "
        "Always consult a qualified compliance professional for final decisions.",
        elem_classes=["disclaimer-banner"],
    )

    with gr.Row(equal_height=False):

        # ---- Left column: input + examples ----
        with gr.Column(scale=2, min_width=320):
            description_input = gr.Textbox(
                label="Describe the AI system to evaluate",
                placeholder=(
                    "e.g. An AI tool that screens job applicant resumes "
                    "and ranks candidates..."
                ),
                lines=5,
                max_lines=12,
                show_label=True,
            )

            run_button = gr.Button(
                "🔍 Run Compliance Check",
                variant="primary",
                elem_id="run-btn",
            )

            gr.Markdown("### 💡 Try an example", elem_classes=["examples-header"])
            gr.Markdown(
                "*Click a scenario to load the full description, then hit **Run Compliance Check**.*",
                elem_classes=["examples-header"],
            )

            # Custom example buttons — gr.Examples truncates long text in its
            # table preview, so we use labelled buttons that load the full text.
            example_scenarios = [
                ("📄 Resume Screener",        EXAMPLES[0][0]),
                ("💬 Customer Support Chatbot", EXAMPLES[1][0]),
                ("🏦 Credit Scoring Tool",    EXAMPLES[2][0]),
                ("🎨 Marketing Image Generator",EXAMPLES[3][0]),
                ("🚜 Warehouse Forklift Safety AI", EXAMPLES[4][0]),
                ("🏥 Medical Device Diagnostic AI", EXAMPLES[5][0]),
            ]
            example_buttons = []
            for label, _ in example_scenarios:
                btn = gr.Button(label, variant="secondary", size="sm")
                example_buttons.append(btn)

            gr.Markdown(
                """
### ℹ️ How this works

**Pipeline steps:**

1. **Intake Agent** — extracts structured fields from your description
   (purpose, data types, decision type, affected users, geography)

2. **GDPR Agent** *(parallel)* — evaluates 16 GDPR checkpoints,
   rating each as `addressed / partial / unaddressed / unclear`

3. **EU AI Act Agent** *(parallel)* — classifies the system into a
   risk tier: `minimal → limited → high → unacceptable`

4. **Aggregator Agent** — merges both reports, applies the
   escalation gate, and produces the final readiness report

**Risk colours:**
- 🟢 **Green** — low risk, likely compliant
- 🟡 **Yellow** — medium risk, action recommended
- 🔴 **Red** — high risk, human review mandatory
                """,
                elem_classes=["left-panel"]
            )

        # ---- Right column: output ----
        with gr.Column(scale=3, min_width=400):
            report_output = gr.Markdown(
                value=(
                    "## 👋 Ready to analyse\n\n"
                    "Enter a description of an AI system on the left and click "
                    "**🔍 Run Compliance Check** to generate a compliance readiness report.\n\n"
                    "---\n"
                    "**The pipeline will:**\n"
                    "1. 🧠 Extract structured fields from your description\n"
                    "2. ⚖️ Evaluate against **16 GDPR checkpoints**\n"
                    "3. 🤖 Classify under **EU AI Act risk tiers**\n"
                    "4. 📋 Produce a unified report with action items\n\n"
                    "🟢 Low risk → green &nbsp;|&nbsp; 🟡 Medium risk → yellow &nbsp;|&nbsp; 🔴 High risk → red"
                ),
                elem_classes=["report-panel"],
            )

    # ---- Wire the Run button ----
    run_button.click(
        fn=run_check,
        inputs=description_input,
        outputs=report_output,
        api_name="compliance_check",
    )

    # Also submit on Enter key (Shift+Enter for newlines in the textbox)
    description_input.submit(
        fn=run_check,
        inputs=description_input,
        outputs=report_output,
    )

    # ---- Wire each example button to load its full text into the input ----
    for btn, (_, full_text) in zip(example_buttons, example_scenarios):
        btn.click(
            fn=lambda t=full_text: t,
            inputs=None,
            outputs=description_input,
        )

    # ---- Footer ----
    gr.Markdown(
        "---\n"
        "*Built with [Google ADK](https://google.github.io/adk-docs/) + "
        "[Gradio](https://www.gradio.app/) · "
        "Powered by GPT-4o-mini via LiteLLM*",
    )


# ---------------------------------------------------------------------------
# Launch
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import sys, io
    # Fix Windows console to handle emoji without crashing
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace", line_buffering=True)

    print("\n" + "=" * 65)
    print("  GDPR + EU AI Act Compliance Co-Pilot")
    print("  Starting Gradio server at http://127.0.0.1:7860")
    print("=" * 65 + "\n")

    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=True,      # Set share=True for a public Gradio link (demo day)
        show_error=True,  # Surface tracebacks in the UI during development
        theme=gr.themes.Soft(
            primary_hue="blue",
            secondary_hue="violet",
            font=[gr.themes.GoogleFont("Inter"), "ui-sans-serif", "sans-serif"],
        ),
        css=CUSTOM_CSS,
    )
