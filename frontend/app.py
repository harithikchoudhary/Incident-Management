import streamlit as st
import requests
import pandas as pd
from datetime import datetime

API_BASE = "http://127.0.0.1:8000"

st.set_page_config(page_title="Incident Management Platform", layout="wide", page_icon="🔧")


def api_get(path, params=None):
    try:
        r = requests.get(f"{API_BASE}{path}", params=params, timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to backend. Make sure the API server is running on port 8000.")
        return None
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return None
        st.error(f"API error: {e}")
        return None
    except Exception as e:
        st.error(f"API error: {e}")
        return None


def api_post(path, data):
    try:
        r = requests.post(f"{API_BASE}{path}", json=data, timeout=120)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to backend. Make sure the API server is running on port 8000.")
        return None
    except requests.exceptions.HTTPError as e:
        detail = ""
        try:
            detail = e.response.json().get("detail", "")
        except Exception:
            pass
        st.error(f"API error ({e.response.status_code}): {detail or str(e)}")
        return None
    except Exception as e:
        st.error(f"API error: {e}")
        return None


def check_backend_health():
    try:
        r = requests.get(f"{API_BASE}/api/health", timeout=5)
        return r.status_code == 200
    except Exception:
        return False


# Sidebar
st.sidebar.title("🔧 Incident Management")
st.sidebar.divider()

# Health check indicator
if check_backend_health():
    st.sidebar.success("Backend: Connected")
else:
    st.sidebar.error("Backend: Disconnected")

st.sidebar.divider()

page = st.sidebar.radio("Navigation", [
    "\U0001f4ac Incident Chat",
    "\U0001f4ca Dashboard",
    "\U0001f4cb Historical Incidents",
    "\U0001f50d Search & Details",
    "\U00002b07\ufe0f Data Ingestion",
])

st.sidebar.divider()
st.sidebar.caption("AI-Powered Incident Management Platform")

# ============ CHAT INTERFACE ============
if page == "\U0001f4ac Incident Chat":
    st.title("\U0001f4ac Incident Management Assistant")
    st.caption("Ask about past incidents, or get resolution recommendations — all in one place.")

    # Initialize chat history
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    # Show helpful tips if no messages yet
    if not st.session_state.chat_messages:
        st.info(
            "**How to use:**\n"
            "- **Ask about past incidents:** _\"What happened when ML users could not log in to the MERC APK and Portal?\"_\n"
            "- **Get resolution help:** _\"How was the Kafka server low-disk-space incident resolved?\"_\n"
            "- **Investigate a failure:** _\"Why were cases stuck at dedupe when the MAS Dedupe API failed?\"_\n\n"
            "All answers are based **only** on ingested historical incident data."
        )

    # Display chat history
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

            # Show analysis card if present
            if msg.get("analysis"):
                analysis = msg["analysis"]
                with st.expander("📋 Detailed Analysis", expanded=False):
                    conf = analysis.get("confidence", 0)
                    conf_level = analysis.get("confidence_level", "LOW")
                    icon_map = {"HIGH": "✅", "MEDIUM": "⚠️", "LOW": "❌"}

                    col1, col2, col3 = st.columns(3)
                    col1.metric("Similarity", f"{conf*100:.0f}%")
                    col2.metric("Confidence", f"{icon_map.get(conf_level, '')} {conf_level}")
                    col3.metric("Matches", len(analysis.get("matched_incidents", [])))

                    if analysis.get("likely_root_cause"):
                        st.write(f"**Root Cause:** {analysis['likely_root_cause']}")

                    if analysis.get("recommended_resolution"):
                        st.write("**Resolution Steps:**")
                        for i, step in enumerate(analysis["recommended_resolution"], 1):
                            st.write(f"  {i}. {step}")

                    if analysis.get("matched_incidents"):
                        st.write("**Matched Historical Incidents:**")
                        for match in analysis["matched_incidents"]:
                            st.write(f"  • {match['incident_id']} ({match['similarity']*100:.0f}%) — {match['reason']}")

                    if analysis.get("evidence"):
                        st.write("**Evidence:**")
                        for ev in analysis["evidence"]:
                            st.write(f"  • Source: {ev['incident_id']} (Thread: {ev.get('source_thread_id', 'N/A')})")

                    if analysis.get("warnings"):
                        for w in analysis["warnings"]:
                            st.warning(w)

    # Chat input
    if prompt := st.chat_input("Describe an incident or ask a question..."):
        # Add user message
        st.session_state.chat_messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get AI response
        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
                history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.chat_messages[:-1]]
                result = api_post("/api/incidents/chat", {
                    "message": prompt,
                    "conversation_history": history,
                })

            if result:
                st.markdown(result["response"])
                assistant_msg = {"role": "assistant", "content": result["response"]}

                if result.get("has_analysis") and result.get("analysis"):
                    analysis = result["analysis"]
                    assistant_msg["analysis"] = analysis

                    with st.expander("📋 Detailed Analysis", expanded=True):
                        conf = analysis.get("confidence", 0)
                        conf_level = analysis.get("confidence_level", "LOW")
                        icon_map = {"HIGH": "✅", "MEDIUM": "⚠️", "LOW": "❌"}

                        col1, col2, col3 = st.columns(3)
                        col1.metric("Similarity", f"{conf*100:.0f}%")
                        col2.metric("Confidence", f"{icon_map.get(conf_level, '')} {conf_level}")
                        col3.metric("Matches", len(analysis.get("matched_incidents", [])))

                        if analysis.get("likely_root_cause"):
                            st.write(f"**Root Cause:** {analysis['likely_root_cause']}")

                        if analysis.get("recommended_resolution"):
                            st.write("**Resolution Steps:**")
                            for i, step in enumerate(analysis["recommended_resolution"], 1):
                                st.write(f"  {i}. {step}")

                        if analysis.get("matched_incidents"):
                            st.write("**Matched Historical Incidents:**")
                            for match in analysis["matched_incidents"]:
                                st.write(f"  • {match['incident_id']} ({match['similarity']*100:.0f}%) — {match['reason']}")

                        if analysis.get("evidence"):
                            st.write("**Evidence:**")
                            for ev in analysis["evidence"]:
                                st.write(f"  • Source: {ev['incident_id']} (Thread: {ev.get('source_thread_id', 'N/A')})")

                        if analysis.get("warnings"):
                            for w in analysis["warnings"]:
                                st.warning(w)

                st.session_state.chat_messages.append(assistant_msg)
            else:
                error_msg = "Sorry, I couldn't process your request. Please check that the backend is running and try again."
                st.markdown(error_msg)
                st.session_state.chat_messages.append({"role": "assistant", "content": error_msg})

    # Clear chat button in sidebar
    if st.sidebar.button("🗑️ Clear Chat", key="clear_chat"):
        st.session_state.chat_messages = []
        st.rerun()

# ============ DASHBOARD ============
elif page == "📊 Dashboard":
    st.title("📊 Incident Management Dashboard")

    col_refresh, _ = st.columns([1, 5])
    with col_refresh:
        if st.button("🔄 Refresh", key="refresh_dashboard"):
            st.rerun()

    data = api_get("/api/dashboard")
    if data:
        st.divider()

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Incidents", data["total_incidents"])
        col2.metric("Resolved", data["resolved_incidents"])
        col3.metric("Applications", len(data["applications_affected"]))
        col4.metric("High Severity", data["high_severity_count"])

        st.divider()

        left_col, right_col = st.columns(2)

        with left_col:
            st.subheader("Applications Affected")
            if data["applications_affected"]:
                for app in sorted(data["applications_affected"]):
                    st.write(f"• {app}")
            else:
                st.info("No applications affected yet.")

        with right_col:
            st.subheader("Top Root Causes")
            if data["top_root_causes"]:
                for rc in data["top_root_causes"]:
                    st.write(f"• **{rc['cause']}** — {rc['count']} occurrence(s)")
            else:
                st.info("No root causes found yet.")

        if data["total_incidents"] == 0:
            st.divider()
            st.warning("No incidents in the system. Go to **Data Ingestion** to load mock data.")

# ============ HISTORICAL INCIDENTS ============
elif page == "📋 Historical Incidents":
    st.title("📋 Historical Incidents")

    col_refresh, col_filter = st.columns([1, 3])
    with col_refresh:
        if st.button("🔄 Refresh", key="refresh_incidents"):
            st.rerun()

    data = api_get("/api/incidents")
    if data and data.get("incidents"):
        incidents = data["incidents"]

        # Filters
        with st.expander("🔽 Filters", expanded=False):
            filter_col1, filter_col2, filter_col3 = st.columns(3)
            apps = sorted(set(i["application"] for i in incidents))
            selected_app = filter_col1.selectbox("Application", ["All"] + apps, key="filter_app")
            severities = ["All", "CRITICAL", "HIGH", "MEDIUM", "LOW"]
            selected_sev = filter_col2.selectbox("Severity", severities, key="filter_sev")
            statuses = ["All"] + sorted(set(i["status"] for i in incidents))
            selected_status = filter_col3.selectbox("Status", statuses, key="filter_status")

        filtered = incidents
        if selected_app != "All":
            filtered = [i for i in filtered if i["application"] == selected_app]
        if selected_sev != "All":
            filtered = [i for i in filtered if i["severity"] == selected_sev]
        if selected_status != "All":
            filtered = [i for i in filtered if i["status"] == selected_status]

        st.caption(f"Showing {len(filtered)} of {len(incidents)} incidents")
        st.divider()

        for inc in filtered:
            severity_icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(inc["severity"], "⚪")
            header = f"{severity_icon} **{inc['incident_id']}** | {inc['application']} | {inc['problem_summary'][:70]}"

            with st.expander(header):
                meta_col1, meta_col2, meta_col3, meta_col4 = st.columns(4)
                meta_col1.write(f"**Application:** {inc['application']}")
                meta_col2.write(f"**Environment:** {inc['environment']}")
                meta_col3.write(f"**Severity:** {inc['severity']}")
                meta_col4.write(f"**Status:** {inc['status']}")

                st.write(f"**Problem:** {inc['problem_summary']}")

                if inc.get("root_cause"):
                    st.write(f"**Root Cause:** {inc['root_cause']}")

                if inc.get("resolution"):
                    st.write("**Resolution Steps:**")
                    for step in inc["resolution"]:
                        st.write(f"  ✅ {step}")

                if inc.get("symptoms"):
                    st.write(f"**Symptoms:** {', '.join(inc['symptoms'])}")

                if inc.get("error_codes"):
                    st.write(f"**Error Codes:** `{'`, `'.join(inc['error_codes'])}`")

                if inc.get("created_at"):
                    st.caption(f"Created: {inc['created_at']}")
    else:
        st.info("No incidents found. Go to **Data Ingestion** to load mock data.")

# ============ UNIFIED SEARCH & DETAILS ============
elif page == "🔍 Search & Details":
    st.title("🔍 Search & Details")
    st.caption("Search by incident ID (e.g., INC-001) or by description/symptoms (e.g., database timeout, HTTP 500)")

    # Initialize session state for current incident and conversation
    if "current_incident_data" not in st.session_state:
        st.session_state.current_incident_data = None
    if "show_conversation" not in st.session_state:
        st.session_state.show_conversation = False

    # Search input
    search_col1, search_col2 = st.columns([3, 1])
    with search_col1:
        query = st.text_input(
            "Search by Incident ID or Description", 
            placeholder="e.g., INC-001 OR database connection pool exhaustion, HTTP 500, timeout",
            key="unified_search"
        )
    with search_col2:
        app_filter = st.text_input("Application (optional)", placeholder="e.g., Payment API")

    # Search/Load button
    search_triggered = st.button("🔎 Search / Load", type="primary", key="unified_search_btn")

    # Process search/load
    if query and search_triggered:
        # Reset conversation state on new search
        st.session_state.show_conversation = False
        
        # Check if input looks like an incident ID (e.g., INC-001, INC001, etc.)
        is_incident_id = query.strip().upper().startswith("INC") or "-" in query[:10]
        
        if is_incident_id:
            # Direct incident lookup
            incident_id = query.strip()
            with st.spinner(f"Loading incident {incident_id}..."):
                data = api_get(f"/api/incidents/{incident_id}")
            
            if data:
                # Store in session state
                st.session_state.current_incident_data = data
            else:
                st.session_state.current_incident_data = None
                st.warning(f"❌ Incident '{incident_id}' not found. Try searching by description instead.")
        else:
            # Clear current incident for semantic search
            st.session_state.current_incident_data = None

    # Add "New Search" button if incident is displayed
    if st.session_state.current_incident_data:
        if st.button("🔄 New Search", key="clear_incident"):
            st.session_state.current_incident_data = None
            st.session_state.show_conversation = False
            st.rerun()

    # Display incident details if available
    if st.session_state.current_incident_data:
        data = st.session_state.current_incident_data
        
        st.divider()
        st.success(f"✅ Incident {data['incident_id']} found")
        st.divider()

        # Header
        severity_icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(data["severity"], "⚪")
        st.subheader(f"{severity_icon} {data['incident_id']} — {data['application']}")

        # Metadata grid
        meta_col1, meta_col2, meta_col3 = st.columns(3)
        meta_col1.write(f"**Application:** {data['application']}")
        meta_col2.write(f"**Environment:** {data['environment']}")
        meta_col3.write(f"**Severity:** {data['severity']}")

        meta_col4, meta_col5, meta_col6 = st.columns(3)
        meta_col4.write(f"**Status:** {data['status']}")
        meta_col5.write(f"**Created:** {data.get('created_at', 'N/A')}")
        meta_col6.write(f"**Resolved:** {data.get('resolved_at', 'N/A')}")

        st.divider()

        # Problem
        st.subheader("Problem")
        st.write(data["problem_summary"])

        # Symptoms
        if data.get("symptoms"):
            st.subheader("Symptoms")
            for s in data["symptoms"]:
                st.write(f"• {s}")

        # Error Codes
        if data.get("error_codes"):
            st.subheader("Error Codes")
            st.code(", ".join(data["error_codes"]))

        # Root Cause
        if data.get("root_cause"):
            st.subheader("Root Cause")
            st.info(data["root_cause"])

        # Resolution
        if data.get("resolution"):
            st.subheader("Resolution Steps")
            for i, step in enumerate(data["resolution"], 1):
                st.write(f"**{i}.** {step}")

        # Source Conversation
        st.divider()
        st.subheader("💬 Original Google Chat Conversation")
        
        # Button to toggle conversation display
        if st.button("📜 Load Source Conversation", key="load_conv"):
            st.session_state.show_conversation = True
            st.rerun()
        
        # Display conversation if toggled
        if st.session_state.show_conversation:
            incident_id = data['incident_id']
            conv_data = api_get(f"/api/incidents/{incident_id}/conversation")
            if conv_data and conv_data.get("conversation"):
                with st.container():
                    st.markdown("---")
                    lines = conv_data["conversation"].split("\n")
                    for line in lines:
                        if line.strip():
                            if "]:" in line:
                                parts = line.split("]:", 1)
                                st.markdown(f"**{parts[0]}]:** {parts[1]}")
                            else:
                                st.text(line)
            elif conv_data:
                st.info("No conversation data available for this incident.")
            else:
                st.warning("Could not load conversation.")
    
    # Semantic search - only when not viewing a specific incident
    elif query and search_triggered:
        with st.spinner("Searching..."):
            params = {"q": query}
            if app_filter:
                params["application"] = app_filter
            results = api_get("/api/incidents/search", params=params)

            if results and results.get("results"):
                st.success(f"✅ Found {results['total']} matching incident(s)")
                st.divider()

                for r in results["results"]:
                    inc = r["incident"]
                    score = r["score"]
                    score_pct = int(score * 100)

                    severity_icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(inc["severity"], "⚪")

                    # Show full details in expander
                    with st.expander(
                        f"{severity_icon} {inc['incident_id']} | {inc['application']} | Match: {score_pct}% | {inc['problem_summary'][:60]}...",
                        expanded=(results['total'] == 1)  # Auto-expand if only one result
                    ):
                        st.progress(score, text=f"Relevance: {score_pct}%")
                        
                        # Metadata
                        meta_col1, meta_col2, meta_col3 = st.columns(3)
                        meta_col1.write(f"**Environment:** {inc['environment']}")
                        meta_col2.write(f"**Severity:** {inc['severity']}")
                        meta_col3.write(f"**Status:** {inc['status']}")
                        
                        st.divider()
                        
                        # Problem
                        st.write(f"**Problem:** {inc['problem_summary']}")
                        
                        # Symptoms
                        if inc.get("symptoms"):
                            st.write("**Symptoms:**")
                            for s in inc["symptoms"]:
                                st.write(f"  • {s}")
                        
                        # Error Codes
                        if inc.get("error_codes"):
                            st.write(f"**Error Codes:** `{'`, `'.join(inc['error_codes'])}`")
                        
                        # Root Cause
                        if inc.get("root_cause"):
                            st.write(f"**Root Cause:** {inc['root_cause']}")
                        
                        # Resolution
                        if inc.get("resolution"):
                            st.write("**Resolution Steps:**")
                            for i, step in enumerate(inc["resolution"], 1):
                                st.write(f"  {i}. {step}")
                        
                        # View full details button
                        st.divider()
                        if st.button(f"📜 View Full Details", key=f"view_{inc['incident_id']}"):
                            st.session_state.current_incident_data = inc
                            st.session_state.show_conversation = False
                            st.rerun()
                            
            elif results:
                st.warning("No matching incidents found. Try different search terms.")
    
    elif search_triggered:
        st.warning("Please enter a search query or incident ID.")


# ============ DATA INGESTION ============
elif page == "⬇️ Data Ingestion":
    st.title("⬇️ Data Ingestion")
    st.caption("Load mock Google Chat conversations and extract structured incidents into the knowledge base.")

    st.divider()

    # Status check
    dashboard = api_get("/api/dashboard")
    if dashboard:
        st.info(f"Current state: **{dashboard['total_incidents']}** incidents in the knowledge base.")

    st.divider()

    st.subheader("Ingest Mock Google Chat Data")
    st.write("""
    This will:
    1. Load conversations from `data/original_incident_data.json`
    2. Group messages by thread
    3. Extract structured incidents using AI
    4. Store incidents in the knowledge base
    5. Index incidents for semantic search

    **Note:** Ingestion is idempotent — running it multiple times will not create duplicates.
    """)

    col_btn, col_status = st.columns([1, 2])
    with col_btn:
        ingest_btn = st.button("🚀 Run Ingestion", type="primary", use_container_width=True)

    if ingest_btn:
        with st.spinner("⏳ Ingesting data... This may take a minute as each conversation is processed."):
            result = api_post("/api/ingestion/mock-chat", {})

        if result:
            st.divider()
            st.success("✅ Ingestion completed successfully!")

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Total Threads", result["total_threads"])
            col2.metric("Incidents Extracted", result["incidents_extracted"])
            col3.metric("Successful", result["successful"])
            col4.metric("Failed", result["failed"])

            if result["failed"] > 0:
                st.warning(f"⚠️ {result['failed']} thread(s) failed to process. Check backend logs for details.")

            st.divider()
            st.write("✅ You can now go to **Historical Incidents** or **Search Incidents** to explore the data.")
            st.write("✅ Use **New Incident Analysis** to test the AI-powered resolution engine.")
